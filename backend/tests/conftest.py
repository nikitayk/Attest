"""Shared fixtures for ATTEST backend tests."""

import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import clear_settings_cache, get_settings


@pytest.fixture(autouse=True)
def _test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide minimal env so Settings loads without a real deploy."""
    clear_settings_cache()

    private_key = Ed25519PrivateKey.generate()
    signing_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    monkeypatch.setenv("ATTEST_SIGNING_KEY_PEM", signing_key_pem)
    monkeypatch.setenv("ATTEST_GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("ATTEST_DATABASE_URL", "postgresql://test:test@localhost/test")

    yield

    clear_settings_cache()


@pytest.fixture
def settings():
    return get_settings()
