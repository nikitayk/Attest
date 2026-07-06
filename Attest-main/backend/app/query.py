"""RAG query and certification — implemented in Steps 1.7–2.2."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import get_settings
from app.crypto import (
    build_merkle_tree,
    canonical_json_bytes,
    get_merkle_proof,
    hash_text,
    load_private_key,
    sign_bytes,
)
from app.ingest import chunk_text
from app.models import AnswerCertificate, CertificateChunk
from app.storage import ManifestStore

if TYPE_CHECKING:
    from app.vectorstore import VectorStore


def generate_answer(query: str, retrieved_chunks: list[str]) -> str:
    """
    Generate answer using Groq LLM with retrieved context.

    Uses locked prompt template: answer ONLY from context, say "I don't know" if insufficient.
    """
    settings = get_settings()
    try:
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)

        # Concatenate chunks with separator
        context = "\n\n---\n\n".join(retrieved_chunks)

        prompt = f"""You answer ONLY from the provided context. If context is insufficient, say "I don't know."
Context:
{context}
Question: {query}
Answer:"""

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )

        return response.choices[0].message.content or "I don't know."
    except Exception:
        fallback = retrieved_chunks[0].strip() if retrieved_chunks else ""
        if not fallback:
            return "I don't know."
        return fallback[:400]


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", text.lower())
        if len(token) >= 3
    }


def _load_preview_chunks(data_dir: Path) -> list[dict[str, str | int]]:
    settings = get_settings()
    preview_chunks: list[dict[str, str | int]] = []

    doc_files = sorted(data_dir.glob("*.md")) + sorted(data_dir.glob("*.txt"))
    for doc_path in doc_files:
        doc_id = doc_path.stem
        text = doc_path.read_text(encoding="utf-8")
        for chunk_index, chunk in enumerate(
            chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        ):
            preview_chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_index": chunk_index,
                    "text": chunk,
                }
            )

    return preview_chunks


async def retrieve_and_answer_preview(
    query: str,
    manifest_store: ManifestStore | None = None,
) -> tuple[str, str | None, AnswerCertificate | None]:
    """Hosted-preview retrieval that avoids loading embeddings on small hosts."""
    settings = get_settings()
    if manifest_store is None:
        manifest_store = ManifestStore()

    manifest = await manifest_store.get_latest_manifest()
    if not manifest:
        return "", "Hosted preview manifest is unavailable.", None

    corpus_dir = settings.resolve_path(settings.data_dir)
    preview_chunks = _load_preview_chunks(corpus_dir)
    if not preview_chunks:
        return "", "Hosted preview corpus is empty.", None

    query_terms = _tokenize(query)

    def score_chunk(entry: dict[str, str | int]) -> tuple[int, int]:
        text = str(entry["text"])
        text_terms = _tokenize(text)
        overlap = len(query_terms & text_terms)
        phrase_bonus = 2 if query.lower() in text.lower() else 0
        return overlap + phrase_bonus, -len(text)

    ranked_chunks = sorted(
        preview_chunks,
        key=score_chunk,
        reverse=True,
    )

    top_chunks = [chunk for chunk in ranked_chunks if score_chunk(chunk)[0] > 0][: settings.top_k]
    if not top_chunks:
        top_chunks = ranked_chunks[: max(1, settings.top_k)]

    chunk_to_global_index: dict[tuple[str, int], int] = {}
    for idx, chunk in enumerate(manifest.chunks):
        chunk_to_global_index[(chunk.doc_id, chunk.chunk_index)] = idx

    merkle_tree = build_merkle_tree([c.hash for c in manifest.chunks])
    certificate_chunks: list[CertificateChunk] = []
    primary_doc_id = str(top_chunks[0]["doc_id"])

    for result in top_chunks:
        doc_id = str(result["doc_id"])
        chunk_index = int(result["chunk_index"])
        chunk_text_value = str(result["text"])

        if await manifest_store.is_quarantined(doc_id):
            return "", "Source integrity check failed — document quarantined.", None

        actual_hash = hash_text(chunk_text_value)
        expected_hash = await manifest_store.get_chunk_hash(doc_id, chunk_index)
        if expected_hash != actual_hash:
            await manifest_store.quarantine_doc(doc_id, f"Preview chunk mismatch at {chunk_index}")
            return "", "Source integrity check failed — document quarantined.", None

        global_index = chunk_to_global_index.get((doc_id, chunk_index))
        if global_index is None:
            return "", f"Chunk index mapping not found: {doc_id}#{chunk_index}", None

        certificate_chunks.append(
            CertificateChunk(
                doc_id=doc_id,
                chunk_index=chunk_index,
                text=chunk_text_value,
                hash=actual_hash,
                merkle_proof=get_merkle_proof(merkle_tree, global_index),
            )
        )

    answer = generate_answer(query, [chunk.text for chunk in certificate_chunks])
    cert_dict = {
        "certificate_id": str(uuid.uuid4()),
        "query": query,
        "answer": answer,
        "chunks": [c.model_dump() for c in certificate_chunks],
        "doc_id": primary_doc_id,
        "merkle_root": manifest.merkle_root,
        "manifest_timestamp": manifest.created_at.isoformat(),
        "embedding_model": manifest.embedding_model,
        "llm_model": settings.groq_model,
    }

    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    cert_dict["signature"] = sign_bytes(canonical_json_bytes(cert_dict), private_key)
    return answer, None, AnswerCertificate(**cert_dict)


async def retrieve_and_answer(
    query: str,
    vector_store: VectorStore | None = None,
    manifest_store: ManifestStore | None = None,
) -> tuple[str, str | None, AnswerCertificate | None]:
    """
    Retrieve top-k chunks, re-hash against manifest, and generate answer with certificate.

    Returns (answer, error, certificate) tuple. If error is not None, answer is withheld.
    """
    settings = get_settings()
    if vector_store is None:
        from app.vectorstore import VectorStore

        vector_store = VectorStore()
    if manifest_store is None:
        manifest_store = ManifestStore()

    # Retrieve top-k chunks
    results = await vector_store.query(query, top_k=settings.top_k)

    if not results:
        return "I don't know.", None, None

    # Get manifest for Merkle proofs
    manifest = await manifest_store.get_latest_manifest()
    if not manifest:
        return "", "No manifest found. Ingest corpus first.", None

    # Build mapping from (doc_id, chunk_index) to global chunk index for Merkle proof
    chunk_to_global_index: dict[tuple[str, int], int] = {}
    for idx, chunk in enumerate(manifest.chunks):
        chunk_to_global_index[(chunk.doc_id, chunk.chunk_index)] = idx

    # Lazy integrity check: re-hash each chunk against manifest
    certificate_chunks: list[CertificateChunk] = []
    primary_doc_id = results[0]["metadata"]["doc_id"]

    for result in results:
        doc_id = result["metadata"]["doc_id"]
        chunk_index = result["metadata"]["chunk_index"]
        chunk_text = result["text"]

        # Check if document is quarantined
        if await manifest_store.is_quarantined(doc_id):
            return "", f"Source integrity check failed — answer withheld, document quarantined.", None

        # Re-hash chunk and compare with manifest
        expected_hash = await manifest_store.get_chunk_hash(doc_id, chunk_index)
        if expected_hash is None:
            return "", f"Chunk not found in manifest: {doc_id}#{chunk_index}", None

        actual_hash = hash_text(chunk_text)
        if actual_hash != expected_hash:
            # Tamper detected — quarantine document
            await manifest_store.quarantine_doc(
                doc_id, f"Chunk hash mismatch at index {chunk_index}"
            )
            return "", f"Source integrity check failed — answer withheld, document quarantined.", None

        # Build Merkle proof for this chunk
        global_index = chunk_to_global_index.get((doc_id, chunk_index))
        if global_index is None:
            return "", f"Chunk index mapping not found: {doc_id}#{chunk_index}", None

        from app.crypto import build_merkle_tree

        all_hashes = [c.hash for c in manifest.chunks]
        merkle_tree = build_merkle_tree(all_hashes)
        merkle_proof = get_merkle_proof(merkle_tree, global_index)

        certificate_chunks.append(
            CertificateChunk(
                doc_id=doc_id,
                chunk_index=chunk_index,
                text=chunk_text,
                hash=actual_hash,
                merkle_proof=merkle_proof,
            )
        )

    # Extract chunk texts
    chunk_texts = [r["text"] for r in results]

    # Generate answer
    answer = generate_answer(query, chunk_texts)

    # Build and sign certificate
    cert_dict = {
        "certificate_id": str(uuid.uuid4()),
        "query": query,
        "answer": answer,
        "chunks": [c.model_dump() for c in certificate_chunks],
        "doc_id": primary_doc_id,
        "merkle_root": manifest.merkle_root,
        "manifest_timestamp": manifest.created_at.isoformat(),
        "embedding_model": manifest.embedding_model,
        "llm_model": settings.groq_model,
    }

    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    signature = sign_bytes(canonical_json_bytes(cert_dict), private_key)
    cert_dict["signature"] = signature

    certificate = AnswerCertificate(**cert_dict)

    return answer, None, certificate
