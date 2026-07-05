"""SQLite manifest, certificates, quarantine — implemented in Step 1.6+."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models import AnswerCertificate, Manifest


class ManifestStore:
    """SQLite storage for manifests and quarantine state."""

    def __init__(self):
        settings = get_settings()
        self.db_path = settings.resolve_path(settings.manifest_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS manifests (
                    manifest_id TEXT PRIMARY KEY,
                    doc_ids TEXT,
                    chunks TEXT,
                    merkle_root TEXT,
                    document_hashes TEXT,
                    created_at TEXT,
                    embedding_model TEXT,
                    chunk_size INTEGER,
                    chunk_overlap INTEGER,
                    signature TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quarantine (
                    doc_id TEXT PRIMARY KEY,
                    quarantined_at TEXT,
                    reason TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS certificates (
                    certificate_id TEXT PRIMARY KEY,
                    query TEXT,
                    answer TEXT,
                    chunks TEXT,
                    doc_id TEXT,
                    merkle_root TEXT,
                    manifest_timestamp TEXT,
                    embedding_model TEXT,
                    llm_model TEXT,
                    signature TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()

    def store_manifest(self, manifest: Manifest) -> None:
        """Store manifest in SQLite."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manifests
                (manifest_id, doc_ids, chunks, merkle_root, document_hashes,
                 created_at, embedding_model, chunk_size, chunk_overlap, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.manifest_id,
                    json.dumps(manifest.doc_ids),
                    json.dumps([c.model_dump() for c in manifest.chunks]),
                    manifest.merkle_root,
                    json.dumps(manifest.document_hashes),
                    manifest.created_at.isoformat(),
                    manifest.embedding_model,
                    manifest.chunk_size,
                    manifest.chunk_overlap,
                    manifest.signature,
                ),
            )
            conn.commit()

    def get_latest_manifest(self) -> Manifest | None:
        """Retrieve the most recent manifest."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM manifests ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None

            return Manifest(
                manifest_id=row[0],
                doc_ids=json.loads(row[1]),
                chunks=json.loads(row[2]),
                merkle_root=row[3],
                document_hashes=json.loads(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                embedding_model=row[6],
                chunk_size=row[7],
                chunk_overlap=row[8],
                signature=row[9],
            )

    def clear_manifest(self) -> None:
        """Remove all stored manifests and quarantine state for an empty corpus reset."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM manifests")
            conn.execute("DELETE FROM quarantine")
            conn.commit()

    def quarantine_doc(self, doc_id: str, reason: str) -> None:
        """Mark a document as quarantined."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO quarantine (doc_id, quarantined_at, reason)
                VALUES (?, ?, ?)
                """,
                (doc_id, datetime.now(timezone.utc).isoformat(), reason),
            )
            conn.commit()

    def is_quarantined(self, doc_id: str) -> bool:
        """Check if a document is quarantined."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM quarantine WHERE doc_id = ?", (doc_id,)
            )
            return cursor.fetchone() is not None

    def get_chunk_hash(self, doc_id: str, chunk_index: int) -> str | None:
        """Get expected hash for a chunk from manifest."""
        manifest = self.get_latest_manifest()
        if not manifest:
            return None

        for chunk in manifest.chunks:
            if chunk.doc_id == doc_id and chunk.chunk_index == chunk_index:
                return chunk.hash

        return None

    def store_certificate(self, certificate: AnswerCertificate) -> None:
        """Store certificate in SQLite."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO certificates
                (certificate_id, query, answer, chunks, doc_id, merkle_root,
                 manifest_timestamp, embedding_model, llm_model, signature, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    certificate.certificate_id,
                    certificate.query,
                    certificate.answer,
                    json.dumps([c.model_dump() for c in certificate.chunks]),
                    certificate.doc_id,
                    certificate.merkle_root,
                    certificate.manifest_timestamp.isoformat(),
                    certificate.embedding_model,
                    certificate.llm_model,
                    certificate.signature,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_certificate(self, certificate_id: str) -> AnswerCertificate | None:
        """Retrieve certificate by ID."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            return AnswerCertificate(
                certificate_id=row[0],
                query=row[1],
                answer=row[2],
                chunks=json.loads(row[3]),
                doc_id=row[4],
                merkle_root=row[5],
                manifest_timestamp=datetime.fromisoformat(row[6]),
                embedding_model=row[7],
                llm_model=row[8],
                signature=row[9],
            )
