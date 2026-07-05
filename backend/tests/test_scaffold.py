"""Step 1.1 — verify config and models scaffold correctly."""

from datetime import datetime, timezone

from app.config import get_settings
from app.models import (
    AnswerCertificate,
    CertificateChunk,
    ChunkRecord,
    CorpusHealth,
    DocumentHealth,
    Manifest,
    ManifestSummary,
    MonitorStatus,
    QueryRequest,
    QueryResult,
    VerifyResult,
)


def test_settings_load_with_expected_defaults():
    """Settings must load from env and expose locked Part 3.8 defaults."""
    settings = get_settings()

    assert settings.hash_algo == "sha256"
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.top_k == 3
    assert settings.quarantine_on_mismatch is True
    assert settings.anchor_backend == "local"
    assert settings.signing_key_pem.startswith("-----BEGIN PRIVATE KEY-----")


def test_settings_resolve_path_relative_to_backend():
    """Relative paths in config resolve against backend root, not cwd."""
    settings = get_settings()
    resolved = settings.resolve_path(settings.data_dir)

    assert resolved.name == "data"
    assert resolved.parent.name == "backend"


def test_models_import_and_round_trip_json():
    """Pydantic models must serialize/deserialize for API and storage boundaries."""
    now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)

    manifest = Manifest(
        manifest_id="m-1",
        doc_ids=["hr-policy"],
        chunks=[ChunkRecord(doc_id="hr-policy", chunk_index=0, hash="abc123")],
        merkle_root="root",
        document_hashes={"hr-policy": "dochash"},
        created_at=now,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chunk_size=500,
        chunk_overlap=50,
        signature="sig",
    )
    assert Manifest.model_validate_json(manifest.model_dump_json()).manifest_id == "m-1"

    cert = AnswerCertificate(
        certificate_id="c-1",
        query="What is the PTO policy?",
        answer="10 days.",
        chunks=[
            CertificateChunk(
                doc_id="hr-policy",
                chunk_index=0,
                text="Employees receive 10 days PTO.",
                hash="abc123",
                merkle_proof=["sibling1", "sibling2"],
            )
        ],
        doc_id="hr-policy",
        merkle_root="root",
        manifest_timestamp=now,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        llm_model="llama-3.3-70b-versatile",
        signature="sig",
    )
    assert cert.chunks[0].text == "Employees receive 10 days PTO."

    verify = VerifyResult(
        ok=True,
        reason="VALID",
        hash_match=True,
        proof_valid=True,
        signature_valid=True,
    )
    query = QueryResult(ok=True, answer="10 days.", certificate=cert)
    assert QueryRequest(query="test").query == "test"

    summary = ManifestSummary(
        manifest_id="m-1",
        doc_count=1,
        chunk_count=1,
        merkle_root="root",
        created_at=now,
    )
    health = CorpusHealth(
        documents=[
            DocumentHealth(doc_id="hr-policy", status="OK", doc_hash="dochash")
        ],
        quarantined_count=0,
    )
    monitor = MonitorStatus(
        last_run=now,
        quarantined_count=0,
        docs_checked=1,
        mismatches=[],
    )

    assert summary.chunk_count == 1
    assert health.quarantined_count == 0
    assert monitor.docs_checked == 1
    assert verify.ok is True
    assert query.certificate is not None
