"""
Standalone zero-trust verifier — implemented in Step 2.4.

MUST NOT import from app.* — intentionally duplicated crypto logic for zero-trust boundary.
"""

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def hash_text(text: str) -> str:
    """SHA-256 of UTF-8 text, lowercase hex."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_hex_pair(left_hex: str, right_hex: str) -> str:
    """
    Parent node hash: SHA256(left_hex + right_hex) as UTF-8 concatenation.

    Both operands are lowercase hex strings — never raw bytes.
    """
    return hashlib.sha256((left_hex + right_hex).encode("utf-8")).hexdigest()


def verify_merkle_proof(
    leaf_hash: str,
    proof: list[str],
    root: str,
    leaf_index: int,
) -> bool:
    """
    Recompute root from leaf + proof using implicit L/R from leaf_index parity.

    Intentionally duplicated from app.crypto for zero-trust boundary.
    """
    current = leaf_hash
    index = leaf_index

    for sibling in proof:
        if index % 2 == 0:
            current = hash_hex_pair(current, sibling)
        else:
            current = hash_hex_pair(sibling, current)
        index //= 2

    return current == root


def canonical_json_bytes(payload: dict) -> bytes:
    """Canonical signing serialization: sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_public_key(pem: bytes) -> ed25519.Ed25519PublicKey:
    """Load Ed25519 public key from PEM bytes."""
    return load_pem_public_key(pem)


def verify_signature(
    data: bytes, signature_b64: str, public_key: ed25519.Ed25519PublicKey
) -> bool:
    """Verify base64 Ed25519 signature against bytes."""
    try:
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, data)
        return True
    except Exception:
        return False


def verify_certificate(certificate_path: str, public_key_path: str) -> tuple[bool, str]:
    """
    Verify an AnswerCertificate.

    Returns (is_valid, reason) tuple.
    """
    # Load certificate
    try:
        with open(certificate_path, "r", encoding="utf-8") as f:
            cert = json.load(f)
    except Exception as e:
        return False, f"Failed to load certificate: {e}"

    # Load public key
    try:
        with open(public_key_path, "rb") as f:
            public_key_pem = f.read()
        public_key = load_public_key(public_key_pem)
    except Exception as e:
        return False, f"Failed to load public key: {e}"

    # Extract fields
    signature = cert.get("signature")
    if not signature:
        return False, "Certificate missing signature"

    # Verify signature
    cert_copy = cert.copy()
    del cert_copy["signature"]
    try:
        payload_bytes = canonical_json_bytes(cert_copy)
    except Exception as e:
        return False, f"Failed to canonicalize certificate: {e}"

    if not verify_signature(payload_bytes, signature, public_key):
        return False, "Signature verification failed"

    # Verify each chunk
    merkle_root = cert.get("merkle_root")
    if not merkle_root:
        return False, "Certificate missing merkle_root"

    chunks = cert.get("chunks", [])
    if not chunks:
        return False, "Certificate has no chunks"

    for chunk_data in chunks:
        chunk_text = chunk_data.get("text")
        chunk_hash = chunk_data.get("hash")
        merkle_proof = chunk_data.get("merkle_proof", [])
        chunk_index = chunk_data.get("chunk_index", 0)

        if not chunk_text or not chunk_hash:
            return False, f"Chunk missing text or hash: {chunk_data}"

        # Re-hash chunk
        actual_hash = hash_text(chunk_text)
        if actual_hash != chunk_hash:
            return False, f"Chunk hash mismatch at index {chunk_index}"

        # Verify Merkle proof
        if not verify_merkle_proof(chunk_hash, merkle_proof, merkle_root, chunk_index):
            return False, f"Merkle proof verification failed for chunk {chunk_index}"

    # All checks passed
    manifest_timestamp = cert.get("manifest_timestamp", "unknown")
    return True, f"VALID — grounded in unaltered source at {manifest_timestamp}"


def main():
    parser = argparse.ArgumentParser(
        description="Verify ATTEST AnswerCertificate (zero-trust standalone verifier)"
    )
    parser.add_argument(
        "--certificate", required=True, help="Path to certificate JSON file"
    )
    parser.add_argument(
        "--public-key", required=True, help="Path to public key PEM file"
    )
    args = parser.parse_args()

    is_valid, reason = verify_certificate(args.certificate, args.public_key)

    print(reason)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
