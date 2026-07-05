"""Ed25519 signature tests — Step 1.4."""

from app.crypto import (
    canonical_json_bytes,
    generate_keypair,
    load_private_key,
    load_public_key,
    sign_bytes,
    verify_signature,
)


def test_signature_round_trip():
    """Signature generated with private key must verify with matching public key."""
    private_pem, public_pem = generate_keypair()
    private_key = load_private_key(private_pem)
    public_key = load_public_key(public_pem)

    data = b"test manifest payload"
    signature = sign_bytes(data, private_key)

    assert verify_signature(data, signature, public_key)


def test_signature_fails_with_wrong_public_key():
    """Forged signature under wrong identity must fail verification."""
    private_pem_1, public_pem_1 = generate_keypair()
    private_pem_2, public_pem_2 = generate_keypair()

    private_key_1 = load_private_key(private_pem_1)
    public_key_2 = load_public_key(public_pem_2)

    data = b"test manifest payload"
    signature = sign_bytes(data, private_key_1)

    assert not verify_signature(data, signature, public_key_2)


def test_signature_fails_with_tampered_data():
    """Signature must fail when payload is altered after signing."""
    private_pem, public_pem = generate_keypair()
    private_key = load_private_key(private_pem)
    public_key = load_public_key(public_pem)

    original_data = b"original manifest"
    tampered_data = b"tampered manifest"

    signature = sign_bytes(original_data, private_key)

    assert verify_signature(original_data, signature, public_key)
    assert not verify_signature(tampered_data, signature, public_key)


def test_canonical_json_is_deterministic():
    """Canonical JSON serialization must produce identical bytes for same dict."""
    payload = {"b": 2, "a": 1, "c": {"nested": "value"}}
    bytes1 = canonical_json_bytes(payload)
    bytes2 = canonical_json_bytes(payload)

    assert bytes1 == bytes2
    assert bytes1 == b'{"a":1,"b":2,"c":{"nested":"value"}}'


def test_reordered_manifest_preserves_signature_under_canonical_json():
    """Canonical JSON signing ignores dict insertion order for equivalent payloads."""
    private_pem, public_pem = generate_keypair()
    private_key = load_private_key(private_pem)
    public_key = load_public_key(public_pem)

    manifest = {"doc_id": "test", "chunk_count": 5, "merkle_root": "abc123"}
    signature = sign_bytes(canonical_json_bytes(manifest), private_key)

    # Reorder fields
    reordered = {"chunk_count": 5, "doc_id": "test", "merkle_root": "abc123"}

    assert verify_signature(canonical_json_bytes(reordered), signature, public_key)
