"""SQLAlchemy models for Neon Postgres + pgvector schema."""

from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Integer, String, text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Document(Base):
    """Documents table — stores metadata and whole-doc hash."""
    __tablename__ = "documents"

    doc_id = Column(String, primary_key=True)
    source = Column(String, nullable=False)  # 'demo' | 'upload'
    status = Column(String, nullable=False, default="OK")  # 'OK' | 'QUARANTINED'
    doc_hash = Column(String, nullable=False)  # whole-doc hash at ingest time
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class Chunk(Base):
    """Chunks table — stores text and pgvector embedding."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String, nullable=False)  # Foreign key reference
    chunk_index = Column(Integer, nullable=False)
    text = Column(String, nullable=False)  # MUTABLE — this is what gets "tampered"
    embedding = Column(Vector(384))  # MiniLM-L6-v2 dimension

    __table_args__ = (
        UniqueConstraint('doc_id', 'chunk_index'),
    )


class Manifest(Base):
    """Manifests table — stores signed Merkle root and chunk hashes."""
    __tablename__ = "manifests"

    manifest_id = Column(String, primary_key=True)
    merkle_root = Column(String, nullable=False)
    chunk_hashes = Column(JSON, nullable=False)  # IMMUTABLE ground truth: {doc_id, chunk_index, hash}[]
    signature = Column(String, nullable=False)  # Ed25519 over canonical JSON
    embedding_model = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class Certificate(Base):
    """Certificates table — stores answer certificates."""
    __tablename__ = "certificates"

    certificate_id = Column(String, primary_key=True)
    query = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    cert_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
