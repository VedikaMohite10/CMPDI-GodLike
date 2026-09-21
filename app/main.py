"""FastAPI application factory.

Responsibilities:
- Register all routers
- Configure CORS (permissive for dev — see TODO below)
- On startup: run Alembic migrations + create Qdrant collection
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import documents, pages, search
from app.routers import facts, entities, conflicts, flags, duplicates
# Phase 3 routers
from app.routers import query as query_router
from app.routers import analytics as analytics_router
# Phase 4 routers
from app.routers import reports as reports_router
from app.routers import topics as topics_router
from app.routers import review as review_router
from app.routers import dashboard as dashboard_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting up CMPDI API…")

    # -----------------------------------------------------------------
    # Run pending Alembic migrations automatically on start
    # This ensures the schema is always current without manual steps.
    # -----------------------------------------------------------------
    try:
        import subprocess, sys
        from pathlib import Path as _Path
        project_root = str(_Path(__file__).parent.parent)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        if result.returncode != 0:
            logger.error("Alembic migration failed:\n%s", result.stderr)
        else:
            logger.info("Alembic migrations applied: %s", result.stdout.strip() or "(no changes)")
    except Exception as exc:
        logger.error("Could not run Alembic migrations: %s", exc)

    # -----------------------------------------------------------------
    # Ensure the Qdrant collection exists
    # -----------------------------------------------------------------
    try:
        from app.services.vector.qdrant_indexer import ensure_collection
        await ensure_collection()
        logger.info("Qdrant collection '%s' ready.", settings.QDRANT_COLLECTION_NAME)
    except Exception as exc:
        logger.error("Could not initialise Qdrant collection: %s", exc)

    # -----------------------------------------------------------------
    # Ensure local storage directories exist
    # -----------------------------------------------------------------
    from pathlib import Path
    Path(settings.STORAGE_ROOT, "documents").mkdir(parents=True, exist_ok=True)
    Path(settings.STORAGE_ROOT, "images").mkdir(parents=True, exist_ok=True)
    Path(settings.REPORT_STORAGE_ROOT).mkdir(parents=True, exist_ok=True)

    yield  # ← application runs here

    logger.info("Shutting down CMPDI API.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version="1.0.0-phase4",
        description=(
            "CMPDI AI Mining Intelligence Platform — Phase 4. "
            "Automated Report Generation (PDF/DOCX/XLSX), Word Cloud & Topic Identification, "
            "Human Verification Console (audit trail), and live Data Quality Dashboard. "
            "All numbers are deterministic and evidence-backed; LLM grounded strictly in retrieved data."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------
    # CORS — permissive for dev so any frontend origin can call this API.
    # TODO (Phase 3+): Restrict allow_origins to known frontend origins.
    # TODO (Phase 3+): Add auth middleware before tightening CORS.
    # -----------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,   # must be False when allow_origins=["*"]
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------
    app.include_router(documents.router, prefix="/documents", tags=["Documents"])
    app.include_router(pages.router, prefix="/documents", tags=["Pages"])
    app.include_router(search.router, tags=["Search"])
    # Phase 2 routers
    app.include_router(facts.router)
    app.include_router(entities.router)
    app.include_router(conflicts.router)
    app.include_router(flags.router)
    app.include_router(duplicates.router)
    # Phase 3 — Analytics Engine + AI Query Copilot
    app.include_router(query_router.router)
    app.include_router(analytics_router.router)
    # Phase 4 — Report Generation, Topics, Review Console, Dashboard
    app.include_router(reports_router.router)
    app.include_router(topics_router.router)
    app.include_router(review_router.router)
    app.include_router(dashboard_router.router)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
