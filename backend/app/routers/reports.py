"""Reports router — Phase 4 / Phase 5.

POST /reports/generate
GET  /reports
GET  /reports/{id}
GET  /reports/{id}/export?format=pdf|docx|xlsx

Phase 5 addition: audit log entry written on every successful report generation.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase4 import AuditLog
from app.schemas.reports import (
    ReportGenerateRequest, ReportGenerateResponse,
    ReportContentOut, ReportListItem, ReportScopeOut,
)
from app.services.report.assembler import ReportScope
from app.services.report.report_service import (
    create_report, export_report, get_report, list_reports,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

_MIME_TYPES = {
    "pdf":  "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/generate", response_model=ReportGenerateResponse, status_code=202)
async def generate_report(
    req: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Generate a structured report for the requested scope.

    Returns immediately with the report content and a report_id for export.
    Generation is synchronous here (async background task in Phase 5 if needed).
    """
    label = req.label or f"{req.period_start} to {req.period_end}"
    scope = ReportScope(
        entity_ids=req.entity_ids,
        metrics=req.metrics,
        period_start=req.period_start,
        period_end=req.period_end,
        label=label,
    )
    try:
        db_row = await create_report(db=db, scope=scope)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")

    if db_row.status == "failed":
        raise HTTPException(status_code=500, detail=db_row.error or "Report generation failed.")

    # A1 Audit log — record every successful report generation
    try:
        audit = AuditLog(
            reviewer="system",
            action_type="report_generated",
            target_table="generated_reports",
            target_id=db_row.id,
            before_value=None,
            after_value={
                "status":    db_row.status,
                "label":     label,
                "period_start": str(req.period_start) if req.period_start else None,
                "period_end":   str(req.period_end)   if req.period_end   else None,
                "entity_ids":   [str(e) for e in (req.entity_ids or [])],
            },
            note=f"Report '{label}' generated automatically.",
        )
        db.add(audit)
        await db.commit()
    except Exception:
        pass  # audit failure must never block the response

    scope_out = ReportScopeOut(
        entity_ids=req.entity_ids,
        metrics=req.metrics,
        period_start=req.period_start,
        period_end=req.period_end,
        label=label,
    )
    snapshot = db_row.content_snapshot or {}
    return ReportGenerateResponse(
        report_id=db_row.id,
        status=db_row.status,
        generation_time_seconds=db_row.generation_time_seconds or 0.0,
        scope=scope_out,
        sections=[
            "executive_summary", "production_overview", "historical_trends",
            "comparative_analysis", "data_quality_warnings",
            *( ["recommendations"] if snapshot.get("recommendations") else [] ),
        ],
        citation_count=len(snapshot.get("citations", [])),
        dq_warning_count=snapshot.get("dq_warning_count", 0),
        model_used=db_row.model_used or "",
    )


@router.get("", response_model=PaginatedResponse)
async def list_all_reports(
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows, total = await list_reports(db, page=page, page_size=page_size)
    items = []
    for r in rows:
        scope = r.scope or {}
        items.append({
            "report_id":               str(r.id),
            "status":                  r.status,
            "label":                   scope.get("label"),
            "period_start":            scope.get("period_start"),
            "period_end":              scope.get("period_end"),
            "generation_time_seconds": r.generation_time_seconds,
            "created_at":              r.created_at.isoformat(),
        })
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{report_id}")
async def get_report_content(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return the full structured report content as JSON."""
    row = await get_report(db, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {
        "report_id": str(row.id),
        "status":    row.status,
        "scope":     row.scope,
        "content":   row.content_snapshot,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/{report_id}/export")
async def export_report_file(
    report_id: uuid.UUID,
    format: str = Query(..., pattern="^(pdf|docx|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Download the report as PDF, DOCX, or XLSX."""
    try:
        out_path = await export_report(db=db, report_id=report_id, fmt=format)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")

    mime = _MIME_TYPES.get(format, "application/octet-stream")
    return FileResponse(
        path=str(out_path),
        media_type=mime,
        filename=f"report_{str(report_id)[:8]}.{format}",
    )
