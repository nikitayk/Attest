"""Ingestion pipeline: chunk, hash, Merkle, sign."""

from __future__ import annotations

import gc
import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import get_settings
from app.crypto import (
    build_merkle_tree,
    canonical_json_bytes,
    hash_bytes,
    hash_text,
    load_private_key,
    sign_bytes,
)
from app.models import ChunkRecord, Manifest
from app.storage import ManifestStore

if TYPE_CHECKING:
    from app.vectorstore import VectorStore

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Deterministic character-based sliding window chunker.

    Normalizes BOM and newlines so re-ingest from disk reproduces identical chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(normalized), step):
        piece = normalized[start : start + chunk_size]
        if piece:
            chunks.append(piece)
        if start + chunk_size >= len(normalized):
            break

    return chunks


def _log_memory(label: str) -> None:
    """Log RSS during ingestion when enabled."""
    settings = get_settings()
    if not settings.ingest_log_memory:
        return
    try:
        import psutil

        rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info("Ingest memory [%s]: %.1f MB RSS", label, rss_mb)
    except Exception:
        logger.info("Ingest checkpoint: %s", label)


def extract_text_from_file(doc_path: Path) -> str:
    """Extract normalized UTF-8 text from markdown, text, or PDF corpus files."""
    suffix = doc_path.suffix.lower()
    if suffix == ".pdf":
        import pypdf

        reader = pypdf.PdfReader(str(doc_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = doc_path.read_text(encoding="utf-8")

    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def list_corpus_files(data_dir: Path) -> list[Path]:
    """Return corpus files in deterministic order."""
    return (
        sorted(data_dir.glob("*.md"))
        + sorted(data_dir.glob("*.txt"))
        + sorted(data_dir.glob("*.pdf"))
    )


def build_signed_manifest_from_dir(
    data_dir: Path | None = None,
    *,
    embedding_model: str | None = None,
) -> Manifest:
    """Build and sign a manifest from the source corpus without creating embeddings."""
    settings = get_settings()
    if data_dir is None:
        data_dir = settings.resolve_path(settings.data_dir)

    doc_files = list_corpus_files(data_dir)
    if not doc_files:
        raise ValueError(f"No corpus files found in {data_dir}")

    all_chunks: list[ChunkRecord] = []
    document_hashes: dict[str, str] = {}

    for doc_path in doc_files:
        doc_id = doc_path.stem
        text = extract_text_from_file(doc_path)
        document_hashes[doc_id] = hash_bytes(text.encode("utf-8"))

        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        for idx, chunk in enumerate(chunks):
            all_chunks.append(
                ChunkRecord(
                    doc_id=doc_id,
                    chunk_index=idx,
                    hash=hash_text(chunk),
                )
            )

    manifest_dict = {
        "manifest_id": str(uuid.uuid4()),
        "doc_ids": sorted(document_hashes.keys()),
        "chunks": [c.model_dump() for c in all_chunks],
        "merkle_root": build_merkle_tree([c.hash for c in all_chunks]).root,
        "document_hashes": document_hashes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": embedding_model or settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }

    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    manifest_dict["signature"] = sign_bytes(
        canonical_json_bytes(manifest_dict), private_key
    )
    return Manifest(**manifest_dict)


async def seed_preview_manifest(manifest_store: ManifestStore) -> Manifest:
    """Persist a lightweight manifest for hosted preview mode."""
    settings = get_settings()
    manifest = build_signed_manifest_from_dir(
        embedding_model=settings.preview_embedding_label
    )
    await manifest_store.store_manifest(manifest)
    return manifest


async def _flush_embedding_batch(
    vector_store: VectorStore,
    chunk_ids: list[str],
    texts: list[str],
    metadatas: list[dict[str, str | int]],
) -> None:
    """Embed and persist one batch, then release temporary references."""
    if not texts:
        return

    _log_memory(f"before embed batch ({len(texts)} chunks)")
    embeddings = vector_store.embed_texts(texts)
    await vector_store.add_chunks(chunk_ids, texts, metadatas)
    _log_memory(f"after embed batch ({len(texts)} chunks)")
    gc.collect()


async def ingest_corpus(
    data_dir: Path | None = None,
    vector_store: VectorStore | None = None,
    manifest_store: ManifestStore | None = None,
) -> Manifest:
    """
    Full ingestion pipeline: read docs → chunk → hash → Merkle → sign → store.

    Embeddings are written in batches to keep memory usage bounded on small hosts.
    """
    settings = get_settings()
    if data_dir is None:
        data_dir = settings.resolve_path(settings.data_dir)
    if vector_store is None:
        from app.vectorstore import VectorStore

        vector_store = VectorStore()
    if manifest_store is None:
        manifest_store = ManifestStore()

    _log_memory("start")
    await vector_store.delete_collection()
    await manifest_store.clear_documents()

    doc_files = list_corpus_files(data_dir)
    if not doc_files:
        raise ValueError(f"No corpus files found in {data_dir}")

    all_chunks: list[ChunkRecord] = []
    document_hashes: dict[str, str] = {}
    chunk_ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, str | int]] = []
    batch_size = settings.ingest_batch_size

    for doc_path in doc_files:
        doc_id = doc_path.stem
        text = extract_text_from_file(doc_path)
        document_hashes[doc_id] = hash_bytes(text.encode("utf-8"))

        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        for idx, chunk in enumerate(chunks):
            chunk_hash = hash_text(chunk)
            all_chunks.append(ChunkRecord(doc_id=doc_id, chunk_index=idx, hash=chunk_hash))
            chunk_ids.append(f"{doc_id}#{idx}")
            texts.append(chunk)
            metadatas.append(
                {
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "hash": chunk_hash,
                }
            )

            if len(texts) >= batch_size:
                await _flush_embedding_batch(vector_store, chunk_ids, texts, metadatas)
                chunk_ids, texts, metadatas = [], [], []

    await _flush_embedding_batch(vector_store, chunk_ids, texts, metadatas)

    all_hashes = [c.hash for c in all_chunks]
    merkle_tree = build_merkle_tree(all_hashes)

    manifest_dict = {
        "manifest_id": str(uuid.uuid4()),
        "doc_ids": sorted(document_hashes.keys()),
        "chunks": [c.model_dump() for c in all_chunks],
        "merkle_root": merkle_tree.root,
        "document_hashes": document_hashes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }

    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
    manifest_dict["signature"] = signature

    manifest = Manifest(**manifest_dict)
    await manifest_store.store_manifest(manifest)
    await manifest_store.store_documents(document_hashes)

    _log_memory("complete")
    logger.info(
        "Ingestion complete: %d docs, %d chunks, root=%s...",
        len(manifest.doc_ids),
        len(manifest.chunks),
        manifest.merkle_root[:16],
    )

    return manifest


def create_embeddings(texts: list[str], model_name: str) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI API.

    Kept as a compatibility helper for tests and any callers outside the upload path.
    """
    from openai import OpenAI
    from app.config import get_settings

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(input=texts, model=model_name)
    return [item.embedding for item in response.data]


async def ingest_single_document(
    doc_id: str,
    text: str,
    vector_store: VectorStore,
    manifest_store: ManifestStore,
) -> Manifest:
    """
    Ingest a single document (for upload functionality).

    Creates a new manifest with just this document.
    """
    settings = get_settings()

    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    chunk_hashes = [hash_text(chunk) for chunk in chunks]

    all_chunks = [
        ChunkRecord(doc_id=doc_id, chunk_index=idx, hash=chunk_hash)
        for idx, chunk_hash in enumerate(chunk_hashes)
    ]

    all_hashes = [c.hash for c in all_chunks]
    merkle_tree = build_merkle_tree(all_hashes)

    document_hashes = {doc_id: hash_bytes(text.encode("utf-8"))}

    manifest_dict = {
        "manifest_id": str(uuid.uuid4()),
        "doc_ids": [doc_id],
        "chunks": [c.model_dump() for c in all_chunks],
        "merkle_root": merkle_tree.root,
        "document_hashes": document_hashes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }

    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
    manifest_dict["signature"] = signature

    manifest = Manifest(**manifest_dict)

    embeddings = vector_store.embed_texts(chunks)
    await vector_store.add_documents(doc_id, chunks, embeddings)
    await manifest_store.store_manifest(manifest)
    await manifest_store.store_documents(document_hashes)

    return manifest
