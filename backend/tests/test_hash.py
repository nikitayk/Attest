"""SHA-256 hashing — Step 1.3."""

from app.crypto import hash_text


def test_hash_is_stable():
    """Same input must always produce the same hash."""
    text = "Employees receive 10 days PTO per year."
    digest = hash_text(text)

    assert digest == hash_text(text)
    assert len(digest) == 64
    assert digest == digest.lower()


def test_single_char_change_flips_hash():
    """One character change must completely change the hash — tamper sensitivity."""
    original = "Employees receive 10 days PTO per year."
    tampered = "Employees receive 11 days PTO per year."

    assert hash_text(original) != hash_text(tampered)
