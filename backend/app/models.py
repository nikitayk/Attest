"""Typed contracts for all ATTEST module boundaries."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChunkRecord(BaseModel):
    doc_id: str
    chunk_index: int
    hash: str  # sha256 hex, lowercase


class Manifest(BaseModel):
    manifest_id: str
    doc_ids: list[str]
    chunks: list[ChunkRecord]  # ordered: sorted doc_id, then chunk_index
    merkle_root: str
    document_hashes: dict[str, str]  # doc_id -> whole-file sha256 hex
    created_at: datetime  # UTC
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    signature: str  # base64 Ed25519 over canonical JSON (excludes signature)


class CertificateChunk(BaseModel):
    doc_id: str
    chunk_index: int
    text: str  # required for verification — hash alone proves nothing without text
    hash: str
    merkle_proof: list[str]


class AnswerCertificate(BaseModel):
    certificate_id: str
    query: str
    answer: str
    chunks: list[CertificateChunk]
    doc_id: str  # primary doc cited
    merkle_root: str
    manifest_timestamp: datetime  # UTC
    embedding_model: str
    llm_model: str
    signature: str  # base64 Ed25519 over canonical JSON (excludes signature)


class VerifyResult(BaseModel):
    ok: bool
    reason: str
    hash_match: bool
    proof_valid: bool
    signature_valid: bool


class QueryRequest(BaseModel):
    query: str


class QueryResult(BaseModel):
    ok: bool
    answer: str | None = None
    certificate: AnswerCertificate | None = None
    error: str | None = None  # e.g. tamper / quarantine message


class IngestRequest(BaseModel):
    doc_id: str | None = None  # None = full corpus re-ingest


class ManifestSummary(BaseModel):
    manifest_id: str
    doc_count: int
    chunk_count: int
    merkle_root: str
    created_at: datetime


class DocumentHealth(BaseModel):
    doc_id: str
    status: Literal["OK", "QUARANTINED"]
    doc_hash: str
    last_checked: datetime | None = None


class CorpusHealth(BaseModel):
    documents: list[DocumentHealth]
    quarantined_count: int


class MonitorStatus(BaseModel):
    last_run: datetime | None
    quarantined_count: int
    docs_checked: int
    mismatches: list[str]  # doc_ids quarantined on last run


class AnchorResult(BaseModel):
    backend: str
    anchored: bool
    reference: str | None = None  # Rekor entry ID (stretch) or manifest_id (local)


class VerifyRequest(BaseModel):
    certificate: dict  # AnswerCertificate as dict
    public_key_override: str | None = None  # Optional PEM override for testing


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    doc_hash: str
    message: str


class DocumentList(BaseModel):
    documents: list[dict]  # Each has doc_id, filename, chunk_count, doc_hash, status, uploaded_at
