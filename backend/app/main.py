"""FastAPI application entry — implemented in Step 1.8."""

from __future__ import annotations

import io
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.crypto import canonical_json_bytes, load_public_key, verify_signature, verify_merkle_proof, hash_text
from app.ingest import ingest_corpus
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
from app.query import retrieve_and_answer
from app.storage import ManifestStore
from app.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
_manifest: dict | None = None
_vector_store: VectorStore | None = None
_manifest_store: ManifestStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: reseed-on-boot — wipe and re-ingest corpus on startup."""
    global _manifest, _vector_store, _manifest_store

    logger.info("ATTEST starting up...")
    settings = get_settings()

    # Initialize vector store and manifest store
    _vector_store = VectorStore()
    _manifest_store = ManifestStore()

    # Ingest corpus
    try:
        logger.info(f"Ingesting corpus from {settings.resolve_path(settings.data_dir)}")
        manifest = ingest_corpus(
            vector_store=_vector_store, manifest_store=_manifest_store
        )
        _manifest = manifest.model_dump()
        logger.info(
            f"Ingested {len(manifest.doc_ids)} docs, {len(manifest.chunks)} chunks, "
            f"Merkle root={manifest.merkle_root[:16]}..."
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise

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


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "manifest_loaded": _manifest is not None}


@app.post("/ingest")
def trigger_ingest(request: IngestRequest) -> ManifestSummary:
    """
    Trigger ingestion (full corpus or single doc).

    MVP: full re-ingest only. Single doc re-ingest is stretch.
    """
    global _manifest, _vector_store, _manifest_store

    if _vector_store is None:
        _vector_store = VectorStore()
    if _manifest_store is None:
        _manifest_store = ManifestStore()

    manifest = ingest_corpus(
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
def query_endpoint(request: QueryRequest) -> QueryResult:
    """
    Query the RAG system and return answer with certificate.
    """
    try:
        if _vector_store is None or _manifest_store is None:
            return QueryResult(
                ok=False,
                answer=None,
                certificate=None,
                error="Vector store or manifest store not initialized. Ingest corpus first.",
            )

        answer, error, certificate = retrieve_and_answer(
            request.query, _vector_store, _manifest_store
        )

        if error:
            return QueryResult(ok=False, answer=None, certificate=None, error=error)

        # Store certificate for retrieval
        if certificate and _manifest_store:
            _manifest_store.store_certificate(certificate)

        return QueryResult(
            ok=True,
            answer=answer,
            certificate=certificate,
            error=None,
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return QueryResult(
            ok=False,
            answer=None,
            certificate=None,
            error=str(e),
        )


@app.get("/certificate/{certificate_id}")
def get_certificate(certificate_id: str):
    """Retrieve a certificate by ID."""
    if _manifest_store is None:
        return {"error": "Manifest store not initialized"}

    certificate = _manifest_store.get_certificate(certificate_id)
    if not certificate:
        return {"error": "Certificate not found"}

    return certificate.model_dump()


@app.post("/monitor/trigger")
def trigger_monitor():
    """Trigger full corpus integrity check (called by cron or manual)."""
    if _manifest_store is None:
        return {"error": "Manifest store not initialized"}

    monitor = IntegrityMonitor(_manifest_store)
    status = monitor.trigger_monitor()

    return status.model_dump()


@app.get("/monitor/status")
def get_monitor_status():
    """Get last monitor run status."""
    if _manifest_store is None:
        return {"error": "Manifest store not initialized"}

    monitor = IntegrityMonitor(_manifest_store)
    # Return cached status or run quick check
    # For MVP, run quick check
    status = monitor.trigger_monitor()

    return status.model_dump()


@app.get("/corpus/health")
def get_corpus_health():
    """Get health status of all documents."""
    if _manifest_store is None:
        return {"error": "Manifest store not initialized"}

    monitor = IntegrityMonitor(_manifest_store)
    health = monitor.check_corpus_health()

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
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for ingestion into the RAG system.
    
    Supports: .txt, .md, .pdf files
    The document is chunked, hashed, and added to the vector store.
    The manifest is updated with the new document.
    """
    global _manifest

    if _vector_store is None or _manifest_store is None:
        return {"error": "System not initialized"}

    settings = get_settings()
    
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
        existing_manifest = _manifest_store.get_latest_manifest()
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
            _vector_store.delete_document(doc_id)

        # Add to vector store
        from app.ingest import create_embeddings
        embeddings = create_embeddings(chunks, settings.embedding_model)
        
        # Store in Chroma
        _vector_store.add_documents(
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
            private_key_pem = settings.signing_key_pem
            from app.crypto import load_private_key
            private_key = load_private_key(private_key_pem.encode("utf-8"))

            manifest_dict = new_manifest.model_dump(
                mode="json", exclude={"signature"}
            )
            signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
            new_manifest.signature = signature

            # Store updated manifest
            _manifest_store.store_manifest(new_manifest)
            _manifest = new_manifest.model_dump()
        else:
            # No existing manifest, create new one
            from app.ingest import ingest_single_document
            manifest = ingest_single_document(
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
def list_documents():
    """List all documents in the corpus."""
    if _manifest_store is None:
        return {"error": "System not initialized"}
    
    manifest = _manifest_store.get_latest_manifest()
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
            "status": "QUARANTINED" if _manifest_store.is_quarantined(doc_id) else "OK",
            "uploaded_at": manifest.created_at.isoformat()
        })
    
    return DocumentList(documents=documents)


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """
    Delete a document from the corpus.
    
    This removes the document from the vector store and rebuilds the manifest.
    """
    if _vector_store is None or _manifest_store is None:
        return {"error": "System not initialized"}
    
    manifest = _manifest_store.get_latest_manifest()
    if not manifest or doc_id not in manifest.doc_ids:
        return {"error": "Document not found"}
    
    try:
        # Remove from vector store
        _vector_store.delete_document(doc_id)
        
        # Remove chunks from manifest
        remaining_chunks = sorted(
            [c for c in manifest.chunks if c.doc_id != doc_id],
            key=lambda chunk: (chunk.doc_id, chunk.chunk_index),
        )
        remaining_doc_ids = [d for d in manifest.doc_ids if d != doc_id]
        remaining_doc_hashes = {k: v for k, v in manifest.document_hashes.items() if k != doc_id}
        
        if not remaining_chunks:
            # No documents left, clear manifest
            _manifest_store.clear_manifest()
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
        private_key_pem = settings.signing_key_pem
        from app.crypto import load_private_key
        private_key = load_private_key(private_key_pem.encode("utf-8"))
        
        manifest_dict = new_manifest.model_dump(mode="json", exclude={"signature"})
        signature = sign_bytes(canonical_json_bytes(manifest_dict), private_key)
        new_manifest.signature = signature
        
        # Store updated manifest
        _manifest_store.store_manifest(new_manifest)
        _manifest = new_manifest.model_dump()
        
        logger.info(f"Deleted document: {doc_id}")
        
        return {"message": f"Document {doc_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        return {"error": f"Failed to delete document: {str(e)}"}
