"""Merkle tree — Step 1.3."""

from app.crypto import (
    build_merkle_tree,
    get_merkle_proof,
    hash_text,
    verify_merkle_proof,
)


def test_merkle_root_changes_if_any_leaf_changes():
    """Merkle root must bind all leaves — any leaf change changes the root."""
    leaves = [hash_text(f"chunk-{i}") for i in range(4)]
    tree = build_merkle_tree(leaves)

    tampered = leaves[:]
    tampered[2] = hash_text("tampered chunk")

    tampered_tree = build_merkle_tree(tampered)
    assert tree.root != tampered_tree.root


def test_merkle_proof_valid_for_untampered_chunk():
    """Inclusion proof must verify for an unmodified leaf."""
    leaves = [hash_text(f"chunk-{i}") for i in range(5)]
    tree = build_merkle_tree(leaves)

    for index in range(len(leaves)):
        proof = get_merkle_proof(tree, index)
        assert verify_merkle_proof(leaves[index], proof, tree.root, index)


def test_merkle_proof_fails_for_tampered_chunk():
    """Proof must fail when leaf hash does not match committed content."""
    leaves = [hash_text(f"chunk-{i}") for i in range(4)]
    tree = build_merkle_tree(leaves)

    proof = get_merkle_proof(tree, 1)
    tampered_leaf = hash_text("attacker content")

    assert not verify_merkle_proof(tampered_leaf, proof, tree.root, 1)


def test_merkle_empty_tree_root_is_sha256_empty_string():
    """Empty corpus edge case: root is SHA256('')."""
    tree = build_merkle_tree([])
    assert tree.root == hash_text("")
    assert get_merkle_proof(tree, 0) == []
