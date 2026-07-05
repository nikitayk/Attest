"""Postgres manifest, certificates, quarantine — migrated to Neon + pgvector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.db_models import Base, Certificate, Chunk, Document, Manifest
from app.models import AnswerCertificate, Manifest as ManifestModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class ManifestStore:
    """Postgres storage for manifests and quarantine state."""

    def __init__(self):
        settings = get_settings()
        # Convert postgres:// or postgresql:// to postgresql+asyncpg:// for asyncpg
        # Remove sslmode parameter as asyncpg handles SSL differently
        db_url = settings.database_url.replace("postgres://", "postgresql+asyncpg://").replace("postgresql://", "postgresql+asyncpg://")
        db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def store_manifest(self, manifest: ManifestModel) -> None:
        """Store manifest in Postgres."""
        async with self.async_session() as session:
            # Build chunk_hashes JSONB from manifest chunks
            chunk_hashes = [
                {"doc_id": c.doc_id, "chunk_index": c.chunk_index, "hash": c.hash}
                for c in manifest.chunks
            ]

            db_manifest = Manifest(
                manifest_id=manifest.manifest_id,
                merkle_root=manifest.merkle_root,
                chunk_hashes=chunk_hashes,
                signature=manifest.signature,
                embedding_model=manifest.embedding_model,
                created_at=manifest.created_at,
            )

            session.add(db_manifest)
            await session.commit()

    async def get_latest_manifest(self) -> ManifestModel | None:
        """Retrieve the most recent manifest."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Manifest).order_by(Manifest.created_at.desc()).limit(1)
            )
            db_manifest = result.scalar_one_or_none()

            if not db_manifest:
                return None

            # Reconstruct Manifest model from stored data
            from app.models import ChunkRecord

            chunks = [
                ChunkRecord(
                    doc_id=ch["doc_id"],
                    chunk_index=ch["chunk_index"],
                    hash=ch["hash"],
                )
                for ch in db_manifest.chunk_hashes
            ]

            # Extract doc_ids from chunks
            doc_ids = sorted(set(c.doc_id for c in chunks))

            # Build document_hashes from chunks (simplified - in real impl would store separately)
            document_hashes = {}
            for chunk in chunks:
                if chunk.doc_id not in document_hashes:
                    document_hashes[chunk.doc_id] = ""  # Would need to fetch from documents table

            return ManifestModel(
                manifest_id=db_manifest.manifest_id,
                doc_ids=doc_ids,
                chunks=chunks,
                merkle_root=db_manifest.merkle_root,
                document_hashes=document_hashes,
                created_at=db_manifest.created_at,
                embedding_model=db_manifest.embedding_model,
                chunk_size=500,  # Would need to store in manifest
                chunk_overlap=50,  # Would need to store in manifest
                signature=db_manifest.signature,
            )

    async def clear_manifest(self) -> None:
        """Remove all stored manifests for an empty corpus reset."""
        async with self.async_session() as session:
            await session.execute(select(Manifest).delete())
            await session.commit()

    async def quarantine_doc(self, doc_id: str, reason: str) -> None:
        """Mark a document as quarantined."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Document).where(Document.doc_id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "QUARANTINED"
                await session.commit()

    async def is_quarantined(self, doc_id: str) -> bool:
        """Check if a document is quarantined."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Document.status).where(Document.doc_id == doc_id)
            )
            status = result.scalar_one_or_none()
            return status == "QUARANTINED" if status else False

    async def get_chunk_hash(self, doc_id: str, chunk_index: int) -> str | None:
        """Get expected hash for a chunk from manifest."""
        manifest = await self.get_latest_manifest()
        if not manifest:
            return None

        for chunk in manifest.chunks:
            if chunk.doc_id == doc_id and chunk.chunk_index == chunk_index:
                return chunk.hash

        return None

    async def store_certificate(self, certificate: AnswerCertificate) -> None:
        """Store certificate in Postgres."""
        async with self.async_session() as session:
            db_cert = Certificate(
                certificate_id=certificate.certificate_id,
                query=certificate.query,
                answer=certificate.answer,
                cert_json=certificate.model_dump(),
                created_at=datetime.now(timezone.utc),
            )

            session.add(db_cert)
            await session.commit()

    async def get_certificate(self, certificate_id: str) -> AnswerCertificate | None:
        """Retrieve certificate by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Certificate).where(Certificate.certificate_id == certificate_id)
            )
            db_cert = result.scalar_one_or_none()

            if not db_cert:
                return None

            return AnswerCertificate(**db_cert.cert_json)

    async def get_document_count(self) -> int:
        """Get total number of documents in the corpus."""
        async with self.async_session() as session:
            from sqlalchemy import func

            result = await session.execute(select(func.count()).select_from(Document))
            return result.scalar() or 0
