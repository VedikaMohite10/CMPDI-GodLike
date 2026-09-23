"""FastAPI application factory.

Responsibilities:
- Register all routers
- Configure CORS (configurable via CORS_ALLOWED_ORIGINS env var)
- On startup: run Alembic migrations + create Qdrant collection + bootstrap admin
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.services.auth.dependencies import get_current_user
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
# Phase 5 routers
from app.routers import auth as auth_router
from app.routers import parliamentary as parliamentary_router
from app.routers import map as map_router
from app.routers import forecast as forecast_router
from app.routers import benchmark as benchmark_router

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

    # -----------------------------------------------------------------
    # Phase 5 — Bootstrap admin user (idempotent; skips if any user exists)
    # -----------------------------------------------------------------
    try:
        from app.database import get_db as _get_db
        from app.services.auth.auth_service import ensure_bootstrap_admin
        async for db in _get_db():
            await ensure_bootstrap_admin(db)
            break
    except Exception as exc:
        logger.error("Could not create bootstrap admin: %s", exc)

    yield  # ← application runs here

    logger.info("Shutting down CMPDI API.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version="1.0.0-phase5",
        description=(
            "CMPDI AI Mining Intelligence Platform — Phase 5. "
            "JWT/RBAC Security, Parliamentary Query Copilot, Mining Heat Map, "
            "Forecasting Engine (MA/SES/ARIMA ladder), Benchmarking Harness, "
            "Automated Report Generation, Human Verification Console, and live Data Quality Dashboard. "
            "All numbers are deterministic and evidence-backed; LLM grounded strictly in retrieved data."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------
    # CORS — configurable via CORS_ALLOWED_ORIGINS env var.
    # Set to "*" for dev permissiveness; set to comma-separated origin list
    # for production (e.g. "https://app.example.com,https://admin.example.com").
    # When allow_origins != ["*"], allow_credentials can be True.
    # -----------------------------------------------------------------
    raw_origins = settings.CORS_ALLOWED_ORIGINS.strip()
    if raw_origins == "*":
        allow_origins = ["*"]
        allow_credentials = False  # must be False when allow_origins=["*"]
    else:
        allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        allow_credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------
    # Auth router — login and /me are self-guarded; user creation is admin-guarded
    app.include_router(auth_router.router)

    # Global auth dependency for all other routers (Phase 6 hardening)
    _auth = [Depends(get_current_user)]

    app.include_router(documents.router, prefix="/documents", tags=["Documents"], dependencies=_auth)
    app.include_router(pages.router, prefix="/documents", tags=["Pages"], dependencies=_auth)
    app.include_router(search.router, tags=["Search"], dependencies=_auth)
    # Phase 2 routers
    app.include_router(facts.router, dependencies=_auth)
    app.include_router(entities.router, dependencies=_auth)
    app.include_router(conflicts.router, dependencies=_auth)
    app.include_router(flags.router, dependencies=_auth)
    app.include_router(duplicates.router, dependencies=_auth)
    # Phase 3 — Analytics Engine + AI Query Copilot
    app.include_router(query_router.router, dependencies=_auth)
    app.include_router(analytics_router.router, dependencies=_auth)
    # Phase 4 — Report Generation, Topics, Review Console, Dashboard
    app.include_router(reports_router.router, dependencies=_auth)
    app.include_router(topics_router.router, dependencies=_auth)
    app.include_router(review_router.router, dependencies=_auth)
    app.include_router(dashboard_router.router, dependencies=_auth)
    # Phase 5 — Parliamentary Copilot, Map, Forecast, Benchmark
    app.include_router(parliamentary_router.router, dependencies=_auth)
    app.include_router(map_router.router, dependencies=_auth)
    app.include_router(forecast_router.router, dependencies=_auth)
    app.include_router(benchmark_router.router, dependencies=_auth)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
