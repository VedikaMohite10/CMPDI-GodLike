"""Application configuration — all settings loaded from environment / .env file.

Usage:
    from app.config import get_settings
    settings = get_settings()
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://cmpdi:cmpdipass@localhost:5432/cmpdi_mining"

    # ------------------------------------------------------------------
    # Qdrant
    # ------------------------------------------------------------------
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "mining_text_blocks"
    # bge-m3 produces 1024-dimensional dense vectors
    QDRANT_VECTOR_SIZE: int = 1024

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "bge-m3:latest"
    VLM_MODEL: str = "qwen2.5vl:3b"
    # Timeout (seconds) for a single Ollama call — VLM on CPU can be slow
    OLLAMA_TIMEOUT_SECONDS: int = 300

    # ------------------------------------------------------------------
    # OCR strategy
    # tesseract : always use Tesseract (fast, CPU-friendly)
    # vlm       : always use qwen2.5vl via Ollama (slower on CPU)
    # hybrid    : Tesseract first; fall back to VLM if confidence < threshold
    # ------------------------------------------------------------------
    OCR_ENGINE: str = "tesseract"
    TESSERACT_CONFIDENCE_THRESHOLD: float = 60.0

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    STORAGE_ROOT: str = "./storage"

    # ------------------------------------------------------------------
    # Upload limits
    # ------------------------------------------------------------------
    MAX_FILE_SIZE_MB: int = 100

    # ------------------------------------------------------------------
    # Text chunking for vector indexing
    # Target ~512 tokens; bge-m3 max is 8192 but shorter = better precision
    # ------------------------------------------------------------------
    CHUNK_SIZE_CHARS: int = 1500
    CHUNK_OVERLAP_CHARS: int = 200

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_TITLE: str = "CMPDI AI Mining Intelligence Platform"
    APP_VERSION: str = "1.0.0-phase1"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
