"""Standalone verifier tests for the zero-trust CLI."""

import base64
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Import from verifier to test the zero-trust boundary.
sys.path.insert(0, str(Path(__file__).parent.parent / "verifier"))
from verify import canonical_json_bytes, hash_hex_pair, hash_text, verify_certificate


def _build_signed_certificate(
    private_key: ed25519.Ed25519PrivateKey,
    chunk_text_value: str,
    *,
    chunk_hash: str | None = None,
    merkle_root: str | None = None,
) -> dict:
    """Build a single-chunk certificate signed with the provided key."""
    cert = {
        "certificate_id": "test-cert-1",
        "query": "What is the policy?",
        "answer": "The policy requires X.",
        "chunks": [
            {
                "doc_id": "test-doc",
                "chunk_index": 0,
                "text": chunk_text_value,
                "hash": chunk_hash or hash_text(chunk_text_value),
                "merkle_proof": [],
            }
        ],
        "doc_id": "test-doc",
        "merkle_root": merkle_root or hash_text(chunk_text_value),
        "manifest_timestamp": "2026-07-05T00:00:00Z",
        "embedding_model": "test-model",
        "llm_model": "test-llm",
    }
    signature = private_key.sign(canonical_json_bytes(cert))
    cert["signature"] = base64.b64encode(signature).decode("utf-8")
    return cert


def _write_verifier_inputs(tmp_path: Path, cert: dict, public_pem: bytes) -> tuple[Path, Path]:
    """Write certificate JSON and public key PEM for verifier use."""
    cert_path = tmp_path / "certificate.json"
    key_path = tmp_path / "public_key.pem"
    cert_path.write_text(json.dumps(cert), encoding="utf-8")
    key_path.write_bytes(public_pem)
    return cert_path, key_path


def test_verify_end_to_end_untampered_passes(tmp_path):
    """Full certificate verification passes for unaltered content."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    cert = _build_signed_certificate(
        private_key, "The policy requires X for all employees."
    )
    cert_path, key_path = _write_verifier_inputs(tmp_path, cert, public_pem)

    is_valid, reason = verify_certificate(str(cert_path), str(key_path))

    assert is_valid
    assert "VALID" in reason


def test_verify_end_to_end_tampered_fails(tmp_path):
    """Verification fails when the signed payload contains tampered chunk content."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    original_text = "The policy requires X for all employees."
    cert = _build_signed_certificate(
        private_key,
        "The policy requires Y for all employees.",
        chunk_hash=hash_text(original_text),
        merkle_root=hash_text(original_text),
    )
    cert_path, key_path = _write_verifier_inputs(tmp_path, cert, public_pem)

    is_valid, reason = verify_certificate(str(cert_path), str(key_path))

    assert not is_valid
    assert "hash mismatch" in reason.lower()


def test_verifier_runs_with_backend_offline(tmp_path):
    """CLI runs successfully without importing backend app modules."""
    verifier_path = Path(__file__).parent.parent / "verifier" / "verify.py"
    source = verifier_path.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("app")
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("app")

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    cert = _build_signed_certificate(private_key, "Standalone verifier proof text.")
    cert_path, key_path = _write_verifier_inputs(tmp_path, cert, public_pem)

    completed = subprocess.run(
        [sys.executable, str(verifier_path), "--certificate", str(cert_path), "--public-key", str(key_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "VALID" in completed.stdout


def test_standalone_hash_and_merkle_helpers_match_expected_behavior():
    """Core verifier helpers stay deterministic without backend imports."""
    assert hash_text("test") == hashlib.sha256(b"test").hexdigest()

    leaf = "a"
    root = hash_hex_pair(leaf, leaf)
    from verify import verify_merkle_proof

    assert verify_merkle_proof(leaf, [leaf], root, 0)
