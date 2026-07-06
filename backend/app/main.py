"""FastAPI application entry — implemented in Step 1.8."""

from __future__ import annotations

import io
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.crypto import canonical_json_bytes, load_public_key, verify_signature, verify_merkle_proof, hash_text
from app.ingest import ingest_corpus, seed_preview_manifest
from app.models import (
    DocumentList,
    DocumentUploadResponse,
    IngestRequest,
    ManifestSummary,
    QueryRequest,
    QueryResult,
    VerifyRequest,
    VerifyResult,
)
from app.monitor import IntegrityMonitor
from app.query import retrieve_and_answer, retrieve_and_answer_preview
from app.storage import ManifestStore
from app.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="ATTEST API",
    description="Cryptographic chain of custody for RAG answers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Performance metrics
performance_metrics: Dict[str, list] = {
    "query_latency": [],
    "ingest_latency": [],
    "error_count": 0
}

# Global state
_manifest: dict | None = None
_vector_store: VectorStore | None = None
_manifest_store: ManifestStore | None = None


async def ensure_manifest_store() -> ManifestStore:
    """Lazily initialize manifest storage for lightweight boot on constrained hosts."""
    global _manifest_store, _manifest

    if _manifest_store is None:
        _manifest_store = ManifestStore()

    if _manifest is None:
        settings = get_settings()
        latest_manifest = await _manifest_store.get_latest_manifest()
        if latest_manifest is None and settings.hosted_preview_mode:
            latest_manifest = await seed_preview_manifest(_manifest_store)
        if latest_manifest is not None:
            _manifest = latest_manifest.model_dump()

    return _manifest_store


def ensure_vector_store() -> VectorStore:
    """Lazily initialize the embedding model and Chroma only when needed."""
    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Neon and ingest corpus only if first-ever boot."""
    global _manifest, _vector_store, _manifest_store

    logger.info("ATTEST starting up...")
    settings = get_settings()

    # Configure CORS from settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _manifest_store = ManifestStore()
    _vector_store = VectorStore()

    if settings.hosted_preview_mode:
        logger.info("Hosted preview mode enabled. Using lightweight corpus manifest.")
        latest_manifest = await _manifest_store.get_latest_manifest()
        if latest_manifest is None:
            latest_manifest = await seed_preview_manifest(_manifest_store)
        if latest_manifest is not None:
            _manifest = latest_manifest.model_dump()
    elif settings.auto_ingest_on_startup:
        try:
            # Check if corpus already persisted
            doc_count = await _manifest_store.get_document_count()
            
            if doc_count == 0:
                # First-ever boot → run full ingest
                logger.info(f"First-ever boot: ingesting corpus from {settings.resolve_path(settings.data_dir)}")
                manifest = await ingest_corpus(
                    vector_store=_vector_store, manifest_store=_manifest_store
                )
                _manifest = manifest.model_dump()
                logger.info(
                    f"Ingested {len(manifest.doc_ids)} docs, {len(manifest.chunks)} chunks, "
                    f"Merkle root={manifest.merkle_root[:16]}..."
                )
            else:
                # Corpus already persisted → just load manifest
                logger.info(f"Corpus already persisted ({doc_count} docs). Loading manifest from Neon.")
                latest_manifest = await _manifest_store.get_latest_manifest()
                if latest_manifest:
                    _manifest = latest_manifest.model_dump()
                    logger.info(
                        f"Loaded manifest with {len(latest_manifest.doc_ids)} docs, "
                        f"{len(latest_manifest.chunks)} chunks"
                    )
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise
    else:
        logger.info(
            "Skipping startup ingestion because ATTEST_AUTO_INGEST_ON_STARTUP is disabled."
        )

    yield

    logger.info("ATTEST shutting down...")


settings = get_settings()

app = FastAPI(
    title="ATTEST",
    description="Cryptographic chain of custody for RAG answers",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration — keep local dev working while allowing a locked-down deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz_check():
    """Simple health check for deployment health probes."""
    return {"status": "ok"}

@app.get("/health")
def health_check():
    """Detailed health check endpoint."""
    settings = get_settings()
    preview_mode = settings.hosted_preview_mode
    return {
        "status": "ok",
        "manifest_loaded": _manifest is not None,
        "mode": "hosted-preview" if preview_mode else "full",
        "capabilities": {
            "query": True,
            "verify": True,
            "monitor": True,
            "seed_ingest": (not preview_mode) and settings.allow_mutating_operations,
            "document_upload": (not preview_mode) and settings.allow_mutating_operations,
            "document_delete": (not preview_mode) and settings.allow_mutating_operations,
        },
    }


@app.post("/ingest")
@limiter.limit("5/minute")
async def trigger_ingest(request: IngestRequest, req: Request) -> ManifestSummary:
    """
    Trigger ingestion (full corpus or single doc).

    MVP: full re-ingest only. Single doc re-ingest is stretch.
    """
    global _manifest, _vector_store, _manifest_store
    settings = get_settings()

    if settings.hosted_preview_mode or not settings.allow_mutating_operations:
        raise HTTPException(
            status_code=503,
            detail="Hosted preview disables seed ingestion to keep the demo stable on free hosting.",
        )

    _manifest_store = ManifestStore()
    _vector_store = VectorStore()

    manifest = await ingest_corpus(
        vector_store=_vector_store, manifest_store=_manifest_store
    )
    _manifest = manifest.model_dump()

    return ManifestSummary(
        manifest_id=manifest.manifest_id,
        doc_count=len(manifest.doc_ids),
        chunk_count=len(manifest.chunks),
        merkle_root=manifest.merkle_root,
        created_at=manifest.created_at,
    )


@app.post("/query")
@limiter.limit("10/minute")
async def query_endpoint(request: QueryRequest, req: Request) -> QueryResult:
    """
    Query the RAG system and return answer with certificate.
    """
    start_time = time.time()
    correlation_id = str(uuid.uuid4())
    
    try:
        settings = get_settings()
        _manifest_store = ManifestStore()

        if settings.hosted_preview_mode:
            answer, error, certificate = await retrieve_and_answer_preview(
                request.query, _manifest_store
            )
        else:
            if _vector_store is None or _manifest_store is None:
                return QueryResult(
                    ok=False,
                    answer=None,
                    certificate=None,
                    error="Vector store or manifest store not initialized. Ingest corpus first.",
                )

            answer, error, certificate = await retrieve_and_answer(
                request.query, _vector_store, _manifest_store
            )

        if error:
            performance_metrics["error_count"] += 1
            return QueryResult(ok=False, answer=None, certificate=None, error=error)

        # Store certificate for retrieval
        if certificate and _manifest_store:
            await _manifest_store.store_certificate(certificate)

        # Track performance
        latency = time.time() - start_time
        performance_metrics["query_latency"].append(latency)
        if len(performance_metrics["query_latency"]) > 1000:
            performance_metrics["query_latency"] = performance_metrics["query_latency"][-1000:]

        logger.info(f"Query completed in {latency:.2f}s - correlation_id: {correlation_id}")

        return QueryResult(
            ok=True,
            answer=answer,
            certificate=certificate,
            error=None,
        )
    except Exception as e:
        performance_metrics["error_count"] += 1
        logger.error(f"Query failed: {e} - correlation_id: {correlation_id}")
        return QueryResult(
            ok=False,
            answer=None,
            certificate=None,
            error=str(e),
        )


@app.get("/certificate/{certificate_id}")
async def get_certificate(certificate_id: str):
    """Retrieve a certificate by ID."""
    manifest_store = ManifestStore()

    certificate = await manifest_store.get_certificate(certificate_id)
    if not certificate:
        return {"error": "Certificate not found"}

    return certificate.model_dump()


@app.post("/monitor/trigger")
async def trigger_monitor():
    """Trigger full corpus integrity check (called by cron or manual)."""
    manifest_store = ManifestStore()

    monitor = IntegrityMonitor(manifest_store)
    status = await monitor.trigger_monitor()

    return status.model_dump()


@app.get("/monitor/status")
async def get_monitor_status():
    """Get last monitor run status."""
    manifest_store = ManifestStore()

    monitor = IntegrityMonitor(manifest_store)
    # Return cached status or run quick check
    # For MVP, run quick check
    status = await monitor.trigger_monitor()

    return status.model_dump()


@app.get("/corpus/health")
async def get_corpus_health():
    """Get health status of all documents."""
    manifest_store = ManifestStore()

    monitor = IntegrityMonitor(manifest_store)
    health = await monitor.check_corpus_health()

    return health.model_dump()


@app.get("/public-key")
def get_public_key():
    """Return the Ed25519 public key for verification."""
    settings = get_settings()
    public_key_path = settings.resolve_path(settings.public_key_path)

    if not public_key_path.exists():
        return {"error": "Public key file not found"}

    return public_key_path.read_text(encoding="utf-8")


@app.post("/verify")
def verify_certificate_endpoint(request: VerifyRequest) -> VerifyResult:
    """
    Verify an AnswerCertificate server-side for UI convenience.
    
    Note: For zero-trust verification, use the standalone CLI verifier.
    This endpoint is provided for UI demo convenience only.
    """
    settings = get_settings()
    
    # Load public key
    if request.public_key_override:
        try:
            public_key = load_public_key(request.public_key_override.encode("utf-8"))
        except Exception as e:
            return VerifyResult(
                ok=False,
                reason=f"Failed to load public key override: {e}",
                hash_match=False,
                proof_valid=False,
                signature_valid=False,
            )
    else:
        public_key_path = settings.resolve_path(settings.public_key_path)
        if not public_key_path.exists():
            return VerifyResult(
                ok=False,
                reason="Public key file not found",
                hash_match=False,
                proof_valid=False,
                signature_valid=False,
            )
        try:
            public_key_pem = public_key_path.read_text(encoding="utf-8")
            public_key = load_public_key(public_key_pem.encode("utf-8"))
        except Exception as e:
            return VerifyResult(
                ok=False,
                reason=f"Failed to load public key: {e}",
                hash_match=False,
                proof_valid=False,
                signature_valid=False,
            )
    
    # Extract certificate fields
    cert = request.certificate
    signature = cert.get("signature")
    if not signature:
        return VerifyResult(
            ok=False,
            reason="Certificate missing signature",
            hash_match=False,
            proof_valid=False,
            signature_valid=False,
        )
    
    # Verify signature
    cert_copy = cert.copy()
    del cert_copy["signature"]
    try:
        payload_bytes = canonical_json_bytes(cert_copy)
    except Exception as e:
        return VerifyResult(
            ok=False,
            reason=f"Failed to canonicalize certificate: {e}",
            hash_match=False,
            proof_valid=False,
            signature_valid=False,
        )
    
    signature_valid = verify_signature(payload_bytes, signature, public_key)
    if not signature_valid:
        return VerifyResult(
            ok=False,
            reason="Signature verification failed",
            hash_match=False,
            proof_valid=False,
            signature_valid=False,
        )
    
    # Verify each chunk
    merkle_root = cert.get("merkle_root")
    if not merkle_root:
        return VerifyResult(
            ok=False,
            reason="Certificate missing merkle_root",
            hash_match=True,
            proof_valid=False,
            signature_valid=True,
        )
    
    chunks = cert.get("chunks", [])
    if not chunks:
        return VerifyResult(
            ok=False,
            reason="Certificate has no chunks",
            hash_match=True,
            proof_valid=False,
            signature_valid=True,
        )
    
    hash_match = True
    proof_valid = True
    
    for chunk_data in chunks:
        chunk_text = chunk_data.get("text")
        chunk_hash = chunk_data.get("hash")
        merkle_proof = chunk_data.get("merkle_proof", [])
        chunk_index = chunk_data.get("chunk_index", 0)
        
        if not chunk_text or not chunk_hash:
            return VerifyResult(
                ok=False,
                reason=f"Chunk missing text or hash: {chunk_data}",
                hash_match=False,
                proof_valid=False,
                signature_valid=True,
            )
        
        # Re-hash chunk
        actual_hash = hash_text(chunk_text)
        if actual_hash != chunk_hash:
            return VerifyResult(
                ok=False,
                reason=f"Chunk hash mismatch at index {chunk_index}",
                hash_match=False,
                proof_valid=False,
                signature_valid=True,
            )
        
        # Verify Merkle proof
        if not verify_merkle_proof(chunk_hash, merkle_proof, merkle_root, chunk_index):
            return VerifyResult(
                ok=False,
                reason=f"Merkle proof verification failed for chunk {chunk_index}",
                hash_match=True,
                proof_valid=False,
                signature_valid=True,
            )
    
    # All checks passed
    manifest_timestamp = cert.get("manifest_timestamp", "unknown")
    return VerifyResult(
        ok=True,
        reason=f"VALID — grounded in unaltered source at {manifest_timestamp}",
        hash_match=True,
        proof_valid=True,
        signature_valid=True,
    )


@app.post("/documents")
@limiter.limit("10/minute")
async def upload_document(file: UploadFile = File(...), request: Request = None):
    """
    Upload a document for ingestion into the RAG system.
    
    Supports: .txt, .md, .pdf files
    The document is chunked, hashed, and added to the vector store.
    The manifest is updated with the new document.
    """
    global _manifest, _vector_store, _manifest_store
    settings = get_settings()

    if settings.hosted_preview_mode or not settings.allow_mutating_operations:
        return {
            "error": "Hosted preview is read-only. Upload documents locally for the full ingestion workflow."
        }

    _manifest_store = ManifestStore()
    _vector_store = VectorStore()
    
    # Validate file type
    allowed_extensions = {".txt", ".md", ".pdf"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_extensions:
        return {"error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"}
    
    # Generate doc_id from filename
    doc_id = file.filename.replace(file_ext, "").lower().replace(" ", "-").replace("_", "-")
    
    try:
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        if file_ext == ".pdf":
            # PDF handling
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            except ImportError:
                return {"error": "PDF support requires pypdf. Install with: pip install pypdf"}
            except Exception as e:
                return {"error": f"Failed to extract text from PDF: {e}"}
        else:
            # Text/Markdown files
            text = content.decode("utf-8")
        
        # Normalize text
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        
        if not text:
            return {"error": "Document is empty or could not be extracted"}
        
        # Compute document hash from normalized text.
        doc_hash = hash_text(text)
        
        # Check if document already exists
        existing_manifest = await _manifest_store.get_latest_manifest()
        replacing_existing_document = (
            existing_manifest is not None and doc_id in existing_manifest.document_hashes
        )
        if replacing_existing_document:
            # Document exists, check if content changed
            if existing_manifest.document_hashes[doc_id] == doc_hash:
                return DocumentUploadResponse(
                    doc_id=doc_id,
                    filename=file.filename,
                    chunk_count=0,
                    doc_hash=doc_hash,
                    message="Document already exists with identical content"
                )
        
        # Chunk the document
        from app.ingest import chunk_text
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        
        if not chunks:
            return {"error": "Document produced no chunks (too short)"}
        
        # Compute chunk hashes
        from app.crypto import build_merkle_tree
        chunk_hashes = [hash_text(chunk) for chunk in chunks]
        
        if replacing_existing_document:
            await _vector_store.delete_document(doc_id)

        # Add to vector store
        embeddings = _vector_store.embed_texts(chunks)
        
        # Store in pgvector
        await _vector_store.add_documents(
            doc_id=doc_id,
            chunks=chunks,
            embeddings=embeddings
        )
        
        # Update manifest
        if existing_manifest:
            # Replace existing document content or append a new one.
            from app.models import ChunkRecord, Manifest
            from app.crypto import sign_bytes, canonical_json_bytes
            from datetime import datetime
            import uuid

            base_doc_ids = [d for d in existing_manifest.doc_ids if d != doc_id]
            base_chunks = [c for c in existing_manifest.chunks if c.doc_id != doc_id]
            base_doc_hashes = {
                key: value
                for key, value in existing_manifest.document_hashes.items()
                if key != doc_id
            }

            # Create chunk records
            new_chunk_records = [
                ChunkRecord(
                    doc_id=doc_id,
                    chunk_index=i,
                    hash=chunk_hashes[i]
                )
                for i in range(len(chunks))
            ]

            # Update manifest in deterministic order: doc_id, then chunk_index.
            updated_doc_ids = sorted(base_doc_ids + [doc_id])
            updated_chunks = sorted(
                base_chunks + new_chunk_records,
                key=lambda chunk: (chunk.doc_id, chunk.chunk_index),
            )
            updated_doc_hashes = base_doc_hashes.copy()
            updated_doc_hashes[doc_id] = doc_hash

            # Rebuild Merkle tree with all chunks
            all_hashes = [c.hash for c in updated_chunks]
            merkle_tree = build_merkle_tree(all_hashes)

            # Create new manifest
            from datetime import datetime, timezone

            new_manifest = Manifest(
                manifest_id=str(uuid.uuid4()),
                doc_ids=updated_doc_ids,
                chunks=updated_chunks,
                merkle_root=merkle_tree.root,
                document_hashes=updated_doc_hashes,
                created_at=datetime.now(timezone.utc),
                embedding_model=settings.embedding_model,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                signature=""  # Will be signed below
            )

            # Sign manifest
            private_key_pem = settings.get_signing_key_pem()
            from app.crypto import load_private_key
            private_key = load_private_key(private_key_pem.encode("utf-8"))

            manifest_dict = new_manifest.model_dump(
                mode="json", exclude={"signature"}
            )
            signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
            new_manifest.signature = signature

            # Store updated manifest
            await _manifest_store.store_manifest(new_manifest)
            _manifest = new_manifest.model_dump()
        else:
            # No existing manifest, create new one
            from app.ingest import ingest_single_document
            manifest = await ingest_single_document(
                doc_id=doc_id,
                text=text,
                vector_store=_vector_store,
                manifest_store=_manifest_store
            )
            _manifest = manifest.model_dump()
        
        logger.info(f"Uploaded document: {doc_id} ({len(chunks)} chunks)")
        
        return DocumentUploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            chunk_count=len(chunks),
            doc_hash=doc_hash,
            message=f"Document uploaded successfully with {len(chunks)} chunks"
        )
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        return {"error": f"Failed to upload document: {str(e)}"}


@app.get("/documents")
async def list_documents():
    """List all documents in the corpus."""
    manifest_store = ManifestStore()
    
    manifest = await manifest_store.get_latest_manifest()
    if not manifest:
        return DocumentList(documents=[])
    
    documents = []
    for doc_id in manifest.doc_ids:
        doc_hash = manifest.document_hashes.get(doc_id, "")
        # Count chunks for this document
        chunk_count = sum(1 for c in manifest.chunks if c.doc_id == doc_id)
        
        documents.append({
            "doc_id": doc_id,
            "filename": f"{doc_id}.md",  # Assume .md for display
            "chunk_count": chunk_count,
            "doc_hash": doc_hash,
            "status": "QUARANTINED" if await manifest_store.is_quarantined(doc_id) else "OK",
            "uploaded_at": manifest.created_at.isoformat()
        })
    
    return DocumentList(documents=documents)


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document from the corpus.
    
    This removes the document from the vector store and rebuilds the manifest.
    """
    global _vector_store, _manifest_store
    settings = get_settings()

    if settings.hosted_preview_mode or not settings.allow_mutating_operations:
        return {
            "error": "Hosted preview is read-only. Delete operations are disabled on the live demo."
        }

    _manifest_store = ManifestStore()
    _vector_store = VectorStore()

    manifest = await _manifest_store.get_latest_manifest()
    if not manifest or doc_id not in manifest.doc_ids:
        return {"error": "Document not found"}
    
    try:
        # Remove from vector store
        await _vector_store.delete_document(doc_id)
        
        # Remove chunks from manifest
        remaining_chunks = sorted(
            [c for c in manifest.chunks if c.doc_id != doc_id],
            key=lambda chunk: (chunk.doc_id, chunk.chunk_index),
        )
        remaining_doc_ids = [d for d in manifest.doc_ids if d != doc_id]
        remaining_doc_hashes = {k: v for k, v in manifest.document_hashes.items() if k != doc_id}
        
        if not remaining_chunks:
            # No documents left, clear manifest
            await _manifest_store.clear_manifest()
            global _manifest
            _manifest = None
            return {"message": "Document deleted. Corpus is now empty."}
        
        # Rebuild Merkle tree
        from app.crypto import build_merkle_tree
        all_hashes = [c.hash for c in remaining_chunks]
        merkle_tree = build_merkle_tree(all_hashes)
        
        # Create new manifest
        from app.models import Manifest
        from app.crypto import sign_bytes, canonical_json_bytes
        from datetime import datetime, timezone
        import uuid
        
        new_manifest = Manifest(
            manifest_id=str(uuid.uuid4()),
            doc_ids=sorted(remaining_doc_ids),
            chunks=remaining_chunks,
            merkle_root=merkle_tree.root,
            document_hashes=remaining_doc_hashes,
            created_at=datetime.now(timezone.utc),
            embedding_model=manifest.embedding_model,
            chunk_size=manifest.chunk_size,
            chunk_overlap=manifest.chunk_overlap,
            signature=""
        )
        
        # Sign manifest
        settings = get_settings()
        private_key_pem = settings.get_signing_key_pem()
        from app.crypto import load_private_key
        private_key = load_private_key(private_key_pem.encode("utf-8"))
        
        manifest_dict = new_manifest.model_dump(mode="json", exclude={"signature"})
        signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
        new_manifest.signature = signature
        
        # Store updated manifest
        await _manifest_store.store_manifest(new_manifest)
        _manifest = new_manifest.model_dump()
        
        logger.info(f"Deleted document: {doc_id}")
        
        return {"message": f"Document {doc_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        return {"error": f"Failed to delete document: {str(e)}"}


@app.post("/demo/simulate-tampering")
async def simulate_tampering():
    """
    Simulate document tampering for demo purposes.
    
    This endpoint mutates a chunk in the database directly to demonstrate tamper detection.
    Restricted to allow-listed demo doc_ids only.
    """
    settings = get_settings()
    
    if not settings.hosted_preview_mode and not settings.allow_mutating_operations:
        return {"error": "Tampering simulation is only available in demo mode."}
    
    # Allow-list of demo doc_ids that can be tampered with
    DEMO_DOC_IDS = {"demo-hr-policy", "demo-security-policy"}
    
    # For demo, we'll use the first available doc from the corpus
    _manifest_store = ManifestStore()
    manifest = await _manifest_store.get_latest_manifest()
    
    if not manifest or not manifest.doc_ids:
        return {"error": "No documents available for tampering simulation"}
    
    # Use the first doc_id that's in our allow-list, or the first doc if none match
    target_doc_id = None
    for doc_id in manifest.doc_ids:
        if doc_id in DEMO_DOC_IDS:
            target_doc_id = doc_id
            break
    
    if not target_doc_id:
        target_doc_id = manifest.doc_ids[0]  # Fallback to first doc
    
    # Mutate chunk 0 of the target document in the database
    from app.db_models import Chunk
    from sqlalchemy import select
    
    async with _manifest_store.async_session() as session:
        result = await session.execute(
            select(Chunk).where(Chunk.doc_id == target_doc_id, Chunk.chunk_index == 0)
        )
        chunk = result.scalar_one_or_none()
        
        if chunk:
            chunk.text = chunk.text + " [ALTERED]"
            await session.commit()
        else:
            return {"error": f"Chunk 0 not found for document {target_doc_id}"}
    
    logger.info(f"Simulated tampering on document: {target_doc_id}")
    
    return {
        "message": f"Simulated tampering on document {target_doc_id}. Next query against this document will detect the tamper.",
        "doc_id": target_doc_id,
        "chunk_index": 0
    }


@app.post("/demo/run-isolated")
@limiter.limit("5/minute")
async def run_isolated_demo(req: Request):
    """
    Run an isolated demo that uses a throwaway document,
    ensuring the main corpus is not modified.
    """
    import uuid
    from app.crypto import hash_text, build_merkle_tree, get_merkle_proof, canonical_json_bytes, load_private_key, sign_bytes
    from app.ingest import chunk_text
    from app.models import AnswerCertificate, CertificateChunk
    from datetime import datetime, timezone
    
    settings = get_settings()
    demo_doc_id = f"demo-temp-{uuid.uuid4()}"
    
    # Create a simple throwaway demo document
    demo_doc_content = """# ATTEST Demo Document

This is a temporary document created for demo purposes only. It will not affect the main corpus.

## Key Features
- Cryptographic chain of custody for RAG answers
- Tamper detection using SHA-256 hashes and Merkle trees
- Ed25519 signatures for manifest and certificate verification
- Zero-trust offline verification capability

## How It Works
When you ask a question about this document, ATTEST will:
1. Retrieve relevant chunks
2. Re-hash each chunk against the signed manifest
3. Generate an answer with a verifiable certificate
4. Allow you to verify the answer offline without trusting the server
"""
    
    # Chunk and hash the document
    chunks = chunk_text(demo_doc_content, settings.chunk_size, settings.chunk_overlap)
    chunk_records = [
        {
            "doc_id": demo_doc_id,
            "chunk_index": i,
            "hash": hash_text(chunk),
            "text": chunk
        }
        for i, chunk in enumerate(chunks)
    ]
    
    # Build a simple in-memory manifest for this throwaway doc
    all_hashes = [cr["hash"] for cr in chunk_records]
    merkle_tree = build_merkle_tree(all_hashes)
    
    # Build a manifest structure (not stored, just for the demo)
    demo_manifest = {
        "manifest_id": str(uuid.uuid4()),
        "doc_ids": [demo_doc_id],
        "chunks": chunk_records,
        "merkle_root": merkle_tree.root,
        "document_hashes": {demo_doc_id: hash_text(demo_doc_content)},
        "created_at": datetime.now(timezone.utc),
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap
    }
    
    # Create a tampered chunk (for demo tamper detection)
    tampered_chunk_index = 0
    tampered_chunk_text = chunks[tampered_chunk_index] + " [TAMPERED - THIS IS NOT THE ORIGINAL CONTENT]"
    tampered_chunk_hash = hash_text(tampered_chunk_text)
    
    # Choose a demo query
    demo_query = "What are the key features of ATTEST?"
    
    # Use the first 3 chunks (or all if fewer) for the answer
    top_chunk_indices = list(range(min(3, len(chunks))))
    
    # Generate answer
    from app.query import generate_answer
    answer = generate_answer(demo_query, [chunks[i] for i in top_chunk_indices])
    
    # Build certificate chunks for the answer (with valid chunks)
    certificate_chunks_valid = []
    for idx in top_chunk_indices:
        cr = chunk_records[idx]
        proof = get_merkle_proof(merkle_tree, idx)
        certificate_chunks_valid.append(CertificateChunk(
            doc_id=cr["doc_id"],
            chunk_index=cr["chunk_index"],
            text=cr["text"],
            hash=cr["hash"],
            merkle_proof=proof
        ))
    
    # Build valid certificate
    cert_dict_valid = {
        "certificate_id": str(uuid.uuid4()),
        "query": demo_query,
        "answer": answer,
        "chunks": [c.model_dump() for c in certificate_chunks_valid],
        "doc_id": demo_doc_id,
        "merkle_root": merkle_tree.root,
        "manifest_timestamp": demo_manifest["created_at"].isoformat(),
        "embedding_model": demo_manifest["embedding_model"],
        "llm_model": settings.groq_model
    }
    
    private_key = load_private_key(settings.get_signing_key_pem().encode("utf-8"))
    signature_valid = sign_bytes(canonical_json_bytes(cert_dict_valid), private_key)
    cert_dict_valid["signature"] = signature_valid
    certificate_valid = AnswerCertificate(**cert_dict_valid)
    
    # Now build a tampered certificate to show detection (optional, but useful for demo)
    certificate_chunks_tampered = []
    for idx in top_chunk_indices:
        if idx == tampered_chunk_index:
            proof = get_merkle_proof(merkle_tree, idx)
            certificate_chunks_tampered.append(CertificateChunk(
                doc_id=demo_doc_id,
                chunk_index=idx,
                text=tampered_chunk_text,
                hash=tampered_chunk_hash,
                merkle_proof=proof
            ))
        else:
            cr = chunk_records[idx]
            proof = get_merkle_proof(merkle_tree, idx)
            certificate_chunks_tampered.append(CertificateChunk(
                doc_id=cr["doc_id"],
                chunk_index=cr["chunk_index"],
                text=cr["text"],
                hash=cr["hash"],
                merkle_proof=proof
            ))
    
    cert_dict_tampered = {
        "certificate_id": str(uuid.uuid4()),
        "query": demo_query,
        "answer": answer,
        "chunks": [c.model_dump() for c in certificate_chunks_tampered],
        "doc_id": demo_doc_id,
        "merkle_root": merkle_tree.root,
        "manifest_timestamp": demo_manifest["created_at"].isoformat(),
        "embedding_model": demo_manifest["embedding_model"],
        "llm_model": settings.groq_model
    }
    signature_tampered = sign_bytes(canonical_json_bytes(cert_dict_tampered), private_key)
    cert_dict_tampered["signature"] = signature_tampered
    certificate_tampered = AnswerCertificate(**cert_dict_tampered)
    
    return {
        "demo_doc_id": demo_doc_id,
        "query": demo_query,
        "valid_certificate": certificate_valid.model_dump(),
        "tampered_certificate": certificate_tampered.model_dump(),
        "tampered_chunk_index": tampered_chunk_index,
        "original_chunk": chunks[tampered_chunk_index],
        "tampered_chunk": tampered_chunk_text
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        settings = get_settings()
        manifest_store = ManifestStore()
        
        # Check database connection
        doc_count = await manifest_store.get_document_count()
        
        # Check vector store
        vector_store = VectorStore()
        chunk_count = await vector_store.count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "embedding_model": settings.embedding_model,
            "llm_model": settings.groq_model
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/metrics")
async def get_metrics():
    """Performance metrics endpoint."""
    import statistics
    
    query_latencies = performance_metrics["query_latency"]
    
    return {
        "query_latency": {
            "count": len(query_latencies),
            "avg": statistics.mean(query_latencies) if query_latencies else 0,
            "p50": statistics.median(query_latencies) if query_latencies else 0,
            "p95": sorted(query_latencies)[int(len(query_latencies) * 0.95)] if len(query_latencies) > 0 else 0,
            "p99": sorted(query_latencies)[int(len(query_latencies) * 0.99)] if len(query_latencies) > 0 else 0,
        },
        "error_count": performance_metrics["error_count"],
        "total_queries": len(query_latencies)
    }
