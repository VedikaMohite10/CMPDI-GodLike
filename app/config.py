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
    # Phase 2: Fact extraction LLM — 7b default; set to qwen2.5:14b-instruct-q4_K_M for better accuracy
    FACT_LLM_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"
    # Timeout (seconds) for a single Ollama call — VLM/LLM on CPU can be slow
    OLLAMA_TIMEOUT_SECONDS: int = 300

    # ------------------------------------------------------------------
    # Phase 2 — Data Trust Engine
    # ------------------------------------------------------------------
    # Numeric difference (percent) to trigger a conflict record
    CONFLICT_THRESHOLD_PCT: float = 5.0
    # Minimum cosine similarity for embedding-based entity resolution
    ENTITY_EMBEDDING_THRESHOLD: float = 0.92

    # ------------------------------------------------------------------
    # Phase 3 — Analytics Engine + AI Query Copilot
    # ------------------------------------------------------------------
    # Intent detection / query planning — smaller model; constrained JSON output only
    INTENT_LLM_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"
    # Final answer synthesis — larger model; user-visible natural-language responses
    SYNTHESIS_LLM_MODEL: str = "qwen2.5:14b-instruct-q4_K_M"
    # Minimum Qdrant cosine similarity score to count a semantic result as relevant.
    # Results below this threshold are discarded (Layer 2 of the IE enforcement stack).
    SEMANTIC_RELEVANCE_THRESHOLD: float = 0.60
    # Max retries for intent/plan LLM call before falling back to insufficient-evidence
    QUERY_PLANNER_MAX_RETRIES: int = 2
    # Top-K entities injected into the planner prompt (pre-filtered by embedding similarity
    # to avoid bloating context when the entity table grows large).
    PLANNER_ENTITY_TOP_K: int = 20

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
