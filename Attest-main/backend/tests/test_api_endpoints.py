"""Focused FastAPI endpoint tests with lightweight stubs for heavy runtime deps."""

from __future__ import annotations

import base64
import importlib
import json
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient

from app.config import clear_settings_cache, get_settings
from app.crypto import canonical_json_bytes, hash_text
from app.models import AnswerCertificate, CertificateChunk, ChunkRecord, Manifest


def _install_runtime_dependency_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub optional heavy modules so app.main can import in a lightweight test env."""
    chromadb_module = types.ModuleType("chromadb")

    class _FakeCollection:
        def __init__(self):
            self.name = "attest_chunks"

        def add(self, **kwargs):
            return None

        def query(self, **kwargs):
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        def count(self):
            return 0

        def get(self):
            return {"ids": [], "metadatas": []}

        def delete(self, **kwargs):
            return None

    class _FakeClient:
        def get_or_create_collection(self, **kwargs):
            return _FakeCollection()

        def delete_collection(self, name):
            return None

    chromadb_module.Client = _FakeClient
    chromadb_module.PersistentClient = lambda *args, **kwargs: _FakeClient()

    chromadb_config_module = types.ModuleType("chromadb.config")
    chromadb_config_module.Settings = lambda *args, **kwargs: object()

    sentence_transformers_module = types.ModuleType("sentence_transformers")

    class _FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, texts, show_progress_bar=False):
            class _Encoded:
                def __init__(self, count):
                    self.count = count

                def tolist(self):
                    return [[0.0, 0.0, 0.0] for _ in range(self.count)]

            return _Encoded(len(texts))

    sentence_transformers_module.SentenceTransformer = _FakeSentenceTransformer

    groq_module = types.ModuleType("groq")

    class _FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(
                    create=lambda **kwargs: types.SimpleNamespace(
                        choices=[
                            types.SimpleNamespace(
                                message=types.SimpleNamespace(content="Stub answer")
                            )
                        ]
                    )
                )
            )

    groq_module.Groq = _FakeGroq

    monkeypatch.setitem(sys.modules, "chromadb", chromadb_module)
    monkeypatch.setitem(sys.modules, "chromadb.config", chromadb_config_module)
    monkeypatch.setitem(sys.modules, "sentence_transformers", sentence_transformers_module)
    monkeypatch.setitem(sys.modules, "groq", groq_module)


@pytest.fixture
def main_module(monkeypatch: pytest.MonkeyPatch):
    """Import app.main with heavy runtime dependencies stubbed out."""
    _install_runtime_dependency_stubs(monkeypatch)

    for module_name in ["app.main", "app.query", "app.vectorstore"]:
        sys.modules.pop(module_name, None)

    module = importlib.import_module("app.main")
    return importlib.reload(module)


class DummyVectorStore:
    """Minimal vector store for endpoint tests."""

    def __init__(self):
        self.deleted_doc_ids: list[str] = []
        self.add_calls: list[dict] = []

    def delete_document(self, doc_id: str) -> None:
        self.deleted_doc_ids.append(doc_id)

    def add_documents(self, doc_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
        self.add_calls.append(
            {"doc_id": doc_id, "chunks": chunks, "embeddings": embeddings}
        )


class InMemoryManifestStore:
    """Minimal manifest store covering endpoint behavior under test."""

    def __init__(self, manifest: Manifest | None = None):
        self.manifest = manifest
        self.stored_manifests: list[Manifest] = []
        self.certificates: dict[str, AnswerCertificate] = {}
        self.stored_certificates: list[AnswerCertificate] = []
        self.quarantined: dict[str, str] = {}
        self.cleared = False

    def get_latest_manifest(self) -> Manifest | None:
        return self.manifest

    def store_manifest(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self.stored_manifests.append(manifest)

    def clear_manifest(self) -> None:
        self.manifest = None
        self.cleared = True
        self.quarantined.clear()

    def quarantine_doc(self, doc_id: str, reason: str) -> None:
        self.quarantined[doc_id] = reason

    def is_quarantined(self, doc_id: str) -> bool:
        return doc_id in self.quarantined

    def get_chunk_hash(self, doc_id: str, chunk_index: int) -> str | None:
        if not self.manifest:
            return None
        for chunk in self.manifest.chunks:
            if chunk.doc_id == doc_id and chunk.chunk_index == chunk_index:
                return chunk.hash
        return None

    def store_certificate(self, certificate: AnswerCertificate) -> None:
        self.certificates[certificate.certificate_id] = certificate
        self.stored_certificates.append(certificate)

    def get_certificate(self, certificate_id: str) -> AnswerCertificate | None:
        return self.certificates.get(certificate_id)


def _make_manifest(documents: dict[str, str]) -> Manifest:
    """Build a simple deterministic manifest for a mapping of doc_id -> text."""
    chunks: list[ChunkRecord] = []
    document_hashes: dict[str, str] = {}

    for doc_id in sorted(documents):
        text = documents[doc_id]
        chunks.append(ChunkRecord(doc_id=doc_id, chunk_index=0, hash=hash_text(text)))
        document_hashes[doc_id] = hash_text(text)

    merkle_root = chunks[0].hash if chunks else hash_text("")
    return Manifest(
        manifest_id=str(uuid.uuid4()),
        doc_ids=sorted(documents),
        chunks=chunks,
        merkle_root=merkle_root,
        document_hashes=document_hashes,
        created_at=datetime.now(timezone.utc),
        embedding_model="test-model",
        chunk_size=500,
        chunk_overlap=50,
        signature="test-signature",
    )


def _build_signed_certificate() -> tuple[dict, str]:
    """Create a valid single-chunk certificate and matching PEM public key."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    chunk_text_value = "ATTEST proves provenance for this answer."
    certificate = {
        "certificate_id": "cert-1",
        "query": "What does ATTEST do?",
        "answer": "It proves provenance.",
        "chunks": [
            {
                "doc_id": "alpha",
                "chunk_index": 0,
                "text": chunk_text_value,
                "hash": hash_text(chunk_text_value),
                "merkle_proof": [],
            }
        ],
        "doc_id": "alpha",
        "merkle_root": hash_text(chunk_text_value),
        "manifest_timestamp": "2026-07-05T00:00:00Z",
        "embedding_model": "test-model",
        "llm_model": "test-llm",
    }
    signature = private_key.sign(canonical_json_bytes(certificate))
    certificate["signature"] = base64.b64encode(signature).decode("utf-8")
    return certificate, public_pem


def _make_certificate_model(doc_id: str = "alpha") -> AnswerCertificate:
    """Create a minimal certificate model for API route tests."""
    chunk_text_value = f"{doc_id} chunk text"
    return AnswerCertificate(
        certificate_id=f"cert-{doc_id}",
        query="What is this doc?",
        answer="A test document.",
        chunks=[
            CertificateChunk(
                doc_id=doc_id,
                chunk_index=0,
                text=chunk_text_value,
                hash=hash_text(chunk_text_value),
                merkle_proof=[],
            )
        ],
        doc_id=doc_id,
        merkle_root=hash_text(chunk_text_value),
        manifest_timestamp=datetime.now(timezone.utc),
        embedding_model="test-model",
        llm_model="test-llm",
        signature="test-signature",
    )


def test_health_endpoint_reports_manifest_loaded_state(main_module):
    """Health endpoint reflects whether the in-memory manifest is loaded."""
    main_module._manifest = None
    client = TestClient(main_module.app)

    empty_response = client.get("/health")
    assert empty_response.status_code == 200
    assert empty_response.json() == {"status": "ok", "manifest_loaded": False}

    main_module._manifest = _make_manifest({"alpha": "alpha text"}).model_dump()
    loaded_response = client.get("/health")
    assert loaded_response.status_code == 200
    assert loaded_response.json() == {"status": "ok", "manifest_loaded": True}


def test_ingest_endpoint_returns_manifest_summary(main_module, monkeypatch: pytest.MonkeyPatch):
    """Ingest endpoint rebuilds state and returns manifest metadata."""
    manifest = _make_manifest({"alpha": "alpha text", "beta": "beta text"})
    store = InMemoryManifestStore()
    vector_store = DummyVectorStore()

    monkeypatch.setattr(main_module, "VectorStore", lambda: vector_store)
    monkeypatch.setattr(main_module, "ManifestStore", lambda: store)
    monkeypatch.setattr(
        main_module,
        "ingest_corpus",
        lambda vector_store, manifest_store: manifest,
    )

    main_module._vector_store = None
    main_module._manifest_store = None
    main_module._manifest = None

    client = TestClient(main_module.app)
    response = client.post("/ingest", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest_id"] == manifest.manifest_id
    assert payload["doc_count"] == 2
    assert payload["chunk_count"] == 2
    assert payload["merkle_root"] == manifest.merkle_root
    assert main_module._manifest == manifest.model_dump()


def test_query_endpoint_stores_certificate(main_module, monkeypatch: pytest.MonkeyPatch):
    """Successful queries persist their certificate for later retrieval."""
    store = InMemoryManifestStore(_make_manifest({"alpha": "alpha text"}))
    certificate = _make_certificate_model()

    monkeypatch.setattr(
        main_module,
        "retrieve_and_answer",
        lambda query, vector_store, manifest_store: (
            "Grounded answer",
            None,
            certificate,
        ),
    )

    main_module._manifest_store = store
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)
    response = client.post("/query", json={"query": "What is alpha?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["answer"] == "Grounded answer"
    assert payload["certificate"]["certificate_id"] == certificate.certificate_id
    assert store.stored_certificates == [certificate]


def test_certificate_endpoint_returns_stored_certificate(main_module):
    """Certificate endpoint returns a stored certificate payload."""
    store = InMemoryManifestStore()
    certificate = _make_certificate_model()
    store.store_certificate(certificate)

    main_module._manifest_store = store
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)
    response = client.get(f"/certificate/{certificate.certificate_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["certificate_id"] == certificate.certificate_id
    assert payload["doc_id"] == certificate.doc_id
    assert payload["chunks"][0]["hash"] == certificate.chunks[0].hash


def test_list_documents_surfaces_quarantine_status(main_module):
    """Documents endpoint reports both healthy and quarantined rows."""
    manifest = _make_manifest({"alpha": "alpha text", "beta": "beta text"})
    store = InMemoryManifestStore(manifest)
    store.quarantine_doc("beta", "hash mismatch")

    main_module._manifest_store = store
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)
    response = client.get("/documents")

    assert response.status_code == 200
    payload = response.json()
    statuses = {doc["doc_id"]: doc["status"] for doc in payload["documents"]}
    assert statuses == {"alpha": "OK", "beta": "QUARANTINED"}


def test_delete_last_document_clears_manifest(main_module):
    """Deleting the final document empties corpus state cleanly."""
    manifest = _make_manifest({"alpha": "alpha text"})
    store = InMemoryManifestStore(manifest)
    vector_store = DummyVectorStore()

    main_module._manifest_store = store
    main_module._vector_store = vector_store
    main_module._manifest = manifest.model_dump()

    client = TestClient(main_module.app)
    response = client.delete("/documents/alpha")

    assert response.status_code == 200
    assert response.json()["message"] == "Document deleted. Corpus is now empty."
    assert vector_store.deleted_doc_ids == ["alpha"]
    assert store.cleared is True
    assert main_module._manifest is None


def test_upload_document_replaces_existing_doc(main_module, monkeypatch: pytest.MonkeyPatch):
    """Uploading an existing doc replaces vector entries and stores a new manifest."""
    manifest = _make_manifest({"alpha": "old text"})
    store = InMemoryManifestStore(manifest)
    vector_store = DummyVectorStore()

    import app.ingest as ingest_module

    monkeypatch.setattr(
        ingest_module,
        "create_embeddings",
        lambda texts, model_name: [[0.1, 0.2, 0.3] for _ in texts],
    )

    main_module._manifest_store = store
    main_module._vector_store = vector_store
    main_module._manifest = manifest.model_dump()

    client = TestClient(main_module.app)
    response = client.post(
        "/documents",
        files={"file": ("alpha.txt", b"new corpus text", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["doc_id"] == "alpha"
    assert payload["chunk_count"] == 1
    assert vector_store.deleted_doc_ids == ["alpha"]
    assert vector_store.add_calls[0]["doc_id"] == "alpha"
    assert store.manifest is not None
    assert store.manifest.document_hashes["alpha"] == hash_text("new corpus text")


def test_monitor_endpoints_detect_tampered_doc(
    main_module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Manual monitor endpoints quarantine a doc whose on-disk hash changed."""
    monkeypatch.setenv("ATTEST_DATA_DIR", str(tmp_path))
    clear_settings_cache()

    (tmp_path / "alpha.txt").write_text("tampered text", encoding="utf-8")
    manifest = _make_manifest({"alpha": "original text"})
    store = InMemoryManifestStore(manifest)

    main_module._manifest_store = store
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)

    monitor_response = client.post("/monitor/trigger")
    assert monitor_response.status_code == 200
    assert monitor_response.json()["quarantined_count"] == 1
    assert monitor_response.json()["mismatches"] == ["alpha"]

    health_response = client.get("/corpus/health")
    assert health_response.status_code == 200
    assert health_response.json()["documents"][0]["status"] == "QUARANTINED"


def test_public_key_endpoint_returns_pem(main_module):
    """Public key endpoint serves the verifier PEM."""
    main_module._manifest_store = InMemoryManifestStore()
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)
    response = client.get("/public-key")

    assert response.status_code == 200
    assert "BEGIN PUBLIC KEY" in response.text


def test_verify_endpoint_accepts_valid_certificate(main_module):
    """Server-side verifier accepts a correctly signed certificate."""
    certificate, public_pem = _build_signed_certificate()
    main_module._manifest_store = InMemoryManifestStore()
    main_module._vector_store = DummyVectorStore()

    client = TestClient(main_module.app)
    response = client.post(
        "/verify",
        json={"certificate": certificate, "public_key_override": public_pem},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["signature_valid"] is True
    assert payload["proof_valid"] is True
