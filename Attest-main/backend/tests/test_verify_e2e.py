"""End-to-end verification test — validates full pipeline from ingestion to verification."""

import json
import tempfile
from pathlib import Path

import pytest

from app.crypto import build_merkle_tree, get_merkle_proof, hash_text
from app.ingest import chunk_text
from app.models import AnswerCertificate, CertificateChunk
from app.storage import ManifestStore
from app.vectorstore import VectorStore


def test_verify_end_to_end_untampered_passes():
    """
    Full pipeline test: ingest → query → certificate → verify should pass for untampered data.
    
    This test validates that the entire cryptographic chain works correctly:
    1. Chunk text and compute hashes
    2. Build Merkle tree and generate proofs
    3. Create certificate with proofs
    4. Verify certificate using same logic
    """
    # Sample document
    test_text = "This is a test document for ATTEST. It should be chunked and verified."
    
    # Chunk the text
    chunks = chunk_text(test_text, chunk_size=50, overlap=10)
    assert len(chunks) > 0, "Should produce at least one chunk"
    
    # Compute hashes
    chunk_hashes = [hash_text(chunk) for chunk in chunks]
    
    # Build Merkle tree
    merkle_tree = build_merkle_tree(chunk_hashes)
    merkle_root = merkle_tree.root
    
    # Generate proofs for each chunk
    proofs = [get_merkle_proof(merkle_tree, i) for i in range(len(chunks))]
    
    # Create certificate chunks
    cert_chunks = [
        CertificateChunk(
            doc_id="test-doc",
            chunk_index=i,
            text=chunks[i],
            hash=chunk_hashes[i],
            merkle_proof=proofs[i]
        )
        for i in range(len(chunks))
    ]
    
    # Create certificate (without signature for this test)
    certificate = AnswerCertificate(
        certificate_id="test-cert-1",
        query="What is this document about?",
        answer="This is a test document for ATTEST.",
        chunks=cert_chunks,
        doc_id="test-doc",
        merkle_root=merkle_root,
        manifest_timestamp="2026-07-05T00:00:00Z",
        embedding_model="test-model",
        llm_model="test-llm",
        signature="test-signature"  # Not verifying signature in this test
    )
    
    # Verify each chunk's hash and Merkle proof
    from app.crypto import verify_merkle_proof
    
    for cert_chunk in certificate.chunks:
        # Re-hash chunk text
        actual_hash = hash_text(cert_chunk.text)
        assert actual_hash == cert_chunk.hash, f"Chunk hash mismatch at index {cert_chunk.chunk_index}"
        
        # Verify Merkle proof
        proof_valid = verify_merkle_proof(
            cert_chunk.hash,
            cert_chunk.merkle_proof,
            certificate.merkle_root,
            cert_chunk.chunk_index
        )
        assert proof_valid, f"Merkle proof verification failed for chunk {cert_chunk.chunk_index}"


def test_verify_end_to_end_tampered_fails():
    """
    Full pipeline test: tampered chunk should fail verification.
    
    This test validates that the system detects when chunk text has been altered
    after the certificate was created.
    """
    # Sample document
    test_text = "This is a test document for ATTEST. It should be chunked and verified."
    
    # Chunk the text
    chunks = chunk_text(test_text, chunk_size=50, overlap=10)
    chunk_hashes = [hash_text(chunk) for chunk in chunks]
    
    # Build Merkle tree
    merkle_tree = build_merkle_tree(chunk_hashes)
    merkle_root = merkle_tree.root
    
    # Generate proofs
    proofs = [get_merkle_proof(merkle_tree, i) for i in range(len(chunks))]
    
    # Create certificate with ORIGINAL chunk text
    cert_chunks = [
        CertificateChunk(
            doc_id="test-doc",
            chunk_index=i,
            text=chunks[i],
            hash=chunk_hashes[i],
            merkle_proof=proofs[i]
        )
        for i in range(len(chunks))
    ]
    
    certificate = AnswerCertificate(
        certificate_id="test-cert-2",
        query="What is this document about?",
        answer="This is a test document for ATTEST.",
        chunks=cert_chunks,
        doc_id="test-doc",
        merkle_root=merkle_root,
        manifest_timestamp="2026-07-05T00:00:00Z",
        embedding_model="test-model",
        llm_model="test-llm",
        signature="test-signature"
    )
    
    # TAMPER: Change chunk text but keep original hash
    certificate.chunks[0].text = "TAMPERED: This chunk has been modified!"
    
    # Verify should fail
    from app.crypto import verify_merkle_proof
    
    actual_hash = hash_text(certificate.chunks[0].text)
    assert actual_hash != certificate.chunks[0].hash, "Tampered text should produce different hash"
    
    proof_valid = verify_merkle_proof(
        actual_hash,  # Use actual hash of tampered text
        certificate.chunks[0].merkle_proof,
        certificate.merkle_root,
        certificate.chunks[0].chunk_index
    )
    assert not proof_valid, "Merkle proof should fail for tampered chunk"


def test_verify_with_storage_integration():
    """
    Test verification with actual ManifestStore integration.
    
    This validates that certificates can be stored and retrieved correctly.
    """
    # Create temporary manifest store
    manifest_store = ManifestStore()
    
    # Create a simple certificate
    test_text = "Integration test document"
    chunks = chunk_text(test_text, chunk_size=50, overlap=10)
    chunk_hashes = [hash_text(chunk) for chunk in chunks]
    merkle_tree = build_merkle_tree(chunk_hashes)
    
    cert_chunks = [
        CertificateChunk(
            doc_id="integration-test",
            chunk_index=i,
            text=chunks[i],
            hash=chunk_hashes[i],
            merkle_proof=get_merkle_proof(merkle_tree, i)
        )
        for i in range(len(chunks))
    ]
    
    certificate = AnswerCertificate(
        certificate_id="integration-cert-1",
        query="Integration test query",
        answer="Integration test answer",
        chunks=cert_chunks,
        doc_id="integration-test",
        merkle_root=merkle_tree.root,
        manifest_timestamp="2026-07-05T00:00:00Z",
        embedding_model="test-model",
        llm_model="test-llm",
        signature="test-signature"
    )
    
    # Store certificate
    manifest_store.store_certificate(certificate)
    
    # Retrieve certificate
    retrieved = manifest_store.get_certificate(certificate.certificate_id)
    
    assert retrieved is not None, "Certificate should be retrievable"
    assert retrieved.certificate_id == certificate.certificate_id
    assert retrieved.query == certificate.query
    assert len(retrieved.chunks) == len(certificate.chunks)
    
    # Verify retrieved certificate
    from app.crypto import verify_merkle_proof
    for chunk in retrieved.chunks:
        actual_hash = hash_text(chunk.text)
        assert actual_hash == chunk.hash
        proof_valid = verify_merkle_proof(
            chunk.hash,
            chunk.merkle_proof,
            retrieved.merkle_root,
            chunk.chunk_index
        )
        assert proof_valid
