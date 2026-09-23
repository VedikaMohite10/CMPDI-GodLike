"""Data Quality Dashboard router — Phase 4.

GET /dashboard/stats
GET /dashboard/stats/extraction
GET /dashboard/stats/trust
GET /dashboard/stats/review
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.services.dashboard.dashboard_service import compute_dashboard_stats

router = APIRouter(prefix="/dashboard", tags=["Data Quality Dashboard"])


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    """Full live aggregated data quality metrics.

    All numbers are computed from actual pipeline data — no placeholders.
    Null values indicate insufficient data for that metric; see note_on_nulls.
    """
    return await compute_dashboard_stats(db)


@router.get("/stats/extraction")
async def extraction_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    """Extraction sub-metrics only."""
    full = await compute_dashboard_stats(db)
    return {
        "computed_at": full["computed_at"],
        "extraction":  full["extraction"],
        "pipeline":    full["pipeline"],
    }


@router.get("/stats/trust")
async def trust_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    """Trust / conflict / flag sub-metrics only."""
    full = await compute_dashboard_stats(db)
    return {
        "computed_at":    full["computed_at"],
        "trust":          full["trust"],
        "normalization":  full["normalization"],
    }


@router.get("/stats/review")
async def review_stats(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    """Human review activity sub-metrics only."""
    full = await compute_dashboard_stats(db)
    return {
        "computed_at": full["computed_at"],
        "review":      full["review"],
        "automation":  full["automation"],
    }
