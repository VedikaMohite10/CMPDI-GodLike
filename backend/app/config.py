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
    # Phase 4 — Report Generation
    # ------------------------------------------------------------------
    # Where exported report files are stored on disk (relative to project root)
    REPORT_STORAGE_ROOT: str = "./storage/reports"
    # Max tokens for LLM narrative generation per section (executive summary, etc.)
    REPORT_NARRATIVE_MAX_TOKENS: int = 1024

    # ------------------------------------------------------------------
    # Phase 4 — Topic Clustering
    # ------------------------------------------------------------------
    # Divisor for computing HDBSCAN min_cluster_size = max(3, n_docs // divisor)
    TOPIC_MIN_CLUSTER_SIZE_DIVISOR: int = 20
    # k for k-means fallback when HDBSCAN produces >80% noise or n_docs < 10
    TOPIC_FALLBACK_K: int = 8
    # Top-N TF-IDF keywords to store per cluster
    TOPIC_TOP_KEYWORDS: int = 20

    # ------------------------------------------------------------------
    # Phase 5 — Security / JWT Auth
    # ------------------------------------------------------------------
    # MUST be set via .env — no default to prevent weak-key accidents.
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_A_LONG_RANDOM_STRING"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # Phase 5 — CORS (configurable for real deployments)
    # Default is permissive ("*") for dev; set to comma-separated origin
    # list in .env for production, e.g. "https://app.example.com"
    # ------------------------------------------------------------------
    CORS_ALLOWED_ORIGINS: str = "*"

    # ------------------------------------------------------------------
    # Phase 5 — Rate Limiting (slowapi)
    # Upload endpoint: 10 req/min; Query endpoint: 30 req/min;
    # Global default: 200 req/min
    # ------------------------------------------------------------------
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_QUERY: str = "30/minute"
    RATE_LIMIT_DEFAULT: str = "200/minute"

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_TITLE: str = "CMPDI AI Mining Intelligence Platform"
    APP_VERSION: str = "1.0.0-phase5"
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
