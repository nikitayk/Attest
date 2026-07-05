"""RAG query and certification — implemented in Steps 1.7–2.2."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.config import get_settings
from app.crypto import (
    canonical_json_bytes,
    get_merkle_proof,
    hash_text,
    load_private_key,
    sign_bytes,
)
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
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)

    # Concatenate chunks with separator
    context = "\n\n---\n\n".join(retrieved_chunks)

    prompt = f"""You answer ONLY from the provided context. If context is insufficient, say "I don't know.'
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


def retrieve_and_answer(
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
    results = vector_store.query(query, top_k=settings.top_k)

    if not results:
        return "I don't know.", None, None

    # Get manifest for Merkle proofs
    manifest = manifest_store.get_latest_manifest()
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
        if manifest_store.is_quarantined(doc_id):
            return "", f"Source integrity check failed — answer withheld, document quarantined.", None

        # Re-hash chunk and compare with manifest
        expected_hash = manifest_store.get_chunk_hash(doc_id, chunk_index)
        if expected_hash is None:
            return "", f"Chunk not found in manifest: {doc_id}#{chunk_index}", None

        actual_hash = hash_text(chunk_text)
        if actual_hash != expected_hash:
            # Tamper detected — quarantine document
            manifest_store.quarantine_doc(
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

    private_key = load_private_key(settings.signing_key_pem.encode("utf-8"))
    signature = sign_bytes(canonical_json_bytes(cert_dict), private_key)
    cert_dict["signature"] = signature

    certificate = AnswerCertificate(**cert_dict)

    return answer, None, certificate
