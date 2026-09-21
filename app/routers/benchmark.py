"""Benchmark router — Phase 5.

POST /benchmark/run     — run the harness (admin only)
GET  /benchmark/results — latest + history (analyst+)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase5 import BenchmarkRun, User
from app.services.auth.dependencies import get_current_user, require_role
from app.services.benchmark.benchmark_harness import run_benchmark

router = APIRouter(prefix="/benchmark", tags=["Benchmarking"])


class RunRequest(BaseModel):
    note: Optional[str] = None


def _serialize_run(r: BenchmarkRun) -> dict:
    return {
        "id":                       str(r.id),
        "run_at":                   r.run_at.isoformat(),
        "is_latest":                r.is_latest,
        "document_count_real":      r.document_count_real,
        "document_count_synthetic": r.document_count_synthetic,
        "sample_size":              r.sample_size,
        "run_note":                 r.run_note,
        "results":                  r.results,
    }


@router.post(
    "/run",
    summary="Run the benchmark harness (admin only)",
    description=(
        "Executes the full benchmark harness against the stored ground-truth label sets. "
        "Stores the result as a new BenchmarkRun record (is_latest=True). "
        "Real and synthetic metrics are always reported separately. "
        "Requires admin role."
    ),
)
async def run(
    req: RunRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    try:
        benchmark_run = await run_benchmark(db=db, note=req.note)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Benchmark run failed: {exc}")

    return {
        "message":   "Benchmark run complete.",
        "run_id":    str(benchmark_run.id),
        "run_at":    benchmark_run.run_at.isoformat(),
        "sample_size": benchmark_run.sample_size,
        **benchmark_run.results,
    }


@router.get(
    "/results",
    summary="Get benchmark results (analyst+)",
    description=(
        "Returns the latest benchmark run and historical runs. "
        "Real and synthetic metrics are always in separate keys. "
        "synthetic_doc_ids lists all document IDs from synthetic stress-test documents."
    ),
)
async def results(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    all_runs = (await db.execute(
        select(BenchmarkRun)
        .order_by(BenchmarkRun.run_at.desc())
        .limit(limit)
    )).scalars().all()

    latest = next((r for r in all_runs if r.is_latest), None)

    return {
        "latest":  _serialize_run(latest) if latest else None,
        "history": [_serialize_run(r) for r in all_runs],
        "total_runs": len(all_runs),
    }
