"""Single source of truth for ATTEST configuration."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All runtime configuration. No other module reads os.environ directly."""

    model_config = SettingsConfigDict(
        env_prefix="ATTEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hash_algo: str = "sha256"
    chunk_size: int = 500
    chunk_overlap: int = 50

    signing_key_pem: str | None = Field(
        default=None,
        description="Ed25519 private key PEM (optional - will read from file if not provided)."
    )
    private_key_path: Path = Path("keys/private.pem")
    public_key_path: Path = Path("keys/public_key.pem")
    data_dir: Path = Path("data")
    database_url: str = Field(
        description="Neon Postgres connection string. Required for persistence."
    )

    groq_api_key: str = Field(description="Groq API key for LLM generation.")
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for embeddings (deprecated - using sentence-transformers).")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    preview_embedding_label: str = "preview-lexical-v1"
    top_k: int = 3
    auto_ingest_on_startup: bool = True
    ingest_batch_size: int = 32
    ingest_log_memory: bool = True
    hosted_preview_mode: bool = False
    allow_mutating_operations: bool = True
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    quarantine_on_mismatch: bool = True
    monitor_interval_seconds: int = 900
    anchor_backend: str = "local"  # "local" | "rekor" (stretch)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        """Accept JSON arrays or comma-separated origin lists from env files."""
        if isinstance(value, list):
            return value
        if not value:
            return []

        text = value.strip()
        if text.startswith("["):
            return [str(item).strip() for item in json.loads(text) if str(item).strip()]
        return [origin.strip() for origin in text.split(",") if origin.strip()]

    def resolve_path(self, path: Path) -> Path:
        """Resolve app-relative paths against the backend root."""
        if path.is_absolute():
            return path
        return _BACKEND_ROOT / path

    def get_signing_key_pem(self) -> str:
        """Get signing key PEM from env or file."""
        if self.signing_key_pem:
            return self.signing_key_pem
        # Read from file
        key_path = self.resolve_path(self.private_key_path)
        if key_path.exists():
            return key_path.read_text(encoding="utf-8")
        raise ValueError(f"Signing key not found in env or at {key_path}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings — use in tests after env changes."""
    get_settings.cache_clear()
