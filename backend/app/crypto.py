"""Hash, Merkle tree, and signing helpers."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)


def hash_text(text: str) -> str:
    """SHA-256 of UTF-8 text, lowercase hex."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    """SHA-256 of raw bytes, lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def hash_hex_pair(left_hex: str, right_hex: str) -> str:
    """
    Parent node hash: SHA256(left_hex + right_hex) as UTF-8 concatenation.

    Both operands are lowercase hex strings — never raw bytes.
    """
    return hashlib.sha256((left_hex + right_hex).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MerkleTree:
    root: str
    leaves: list[str]
    levels: list[list[str]]


def build_merkle_tree(leaves: list[str]) -> MerkleTree:
    """
    Binary Merkle tree. Odd levels pad by pairing the last leaf with itself.
    Empty input yields root = SHA256("").
    """
    if not leaves:
        root = hash_text("")
        return MerkleTree(root=root, leaves=[], levels=[[]])

    levels: list[list[str]] = [leaves[:]]
    current = leaves[:]

    while len(current) > 1:
        next_level: list[str] = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            next_level.append(hash_hex_pair(left, right))
        levels.append(next_level)
        current = next_level

    return MerkleTree(root=current[0], leaves=leaves, levels=levels)


def get_merkle_proof(tree: MerkleTree, leaf_index: int) -> list[str]:
    """Sibling hashes from leaf to root (exclusive), using implicit L/R from index parity."""
    if not tree.leaves:
        return []
    if leaf_index < 0 or leaf_index >= len(tree.leaves):
        raise IndexError(f"leaf_index {leaf_index} out of range for {len(tree.leaves)} leaves")

    proof: list[str] = []
    index = leaf_index

    for level in tree.levels[:-1]:
        if index % 2 == 0:
            sibling_index = index + 1
            if sibling_index >= len(level):
                sibling = level[index]  # odd count — last leaf pairs with itself
            else:
                sibling = level[sibling_index]
        else:
            sibling = level[index - 1]

        proof.append(sibling)
        index //= 2

    return proof


def verify_merkle_proof(
    leaf_hash: str,
    proof: list[str],
    root: str,
    leaf_index: int,
) -> bool:
    """
    Recompute root from leaf + proof using implicit L/R from leaf_index parity.

    Must match get_merkle_proof / build_merkle_tree exactly — duplicated in verifier CLI.
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


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Canonical signing serialization: sorted keys, no whitespace, raw UTF-8.

    `ensure_ascii=False` is load-bearing: the browser verifier (frontend/src/lib/verify.js)
    canonicalizes with JSON.stringify, which emits raw UTF-8 and never \\uXXXX-escapes.
    Escaping here would make the two byte streams diverge for any non-ASCII character
    (e.g. an em-dash in an LLM answer), breaking client-side signature verification.
    """
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate Ed25519 keypair: (private_pem, public_pem)."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private_pem, public_pem


def load_private_key(pem: bytes) -> ed25519.Ed25519PrivateKey:
    """Load Ed25519 private key from PEM bytes."""
    return load_pem_private_key(pem, password=None)  # type: ignore


def load_public_key(pem: bytes) -> ed25519.Ed25519PublicKey:
    """Load Ed25519 public key from PEM bytes."""
    return load_pem_public_key(pem)  # type: ignore


def sign_bytes(data: bytes, private_key: ed25519.Ed25519PrivateKey) -> str:
    """Sign bytes with Ed25519, return base64 signature."""
    signature = private_key.sign(data)
    return base64.b64encode(signature).decode("utf-8")


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
