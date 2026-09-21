"""Human Verification Console router — Phase 4.

GET  /review/flags
POST /review/flags/{id}/accept
POST /review/flags/{id}/correct
POST /review/flags/{id}/reject
GET  /review/conflicts
POST /review/conflicts/{id}/resolve
GET  /review/audit-log
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2 import (
    CanonicalEntity, Conflict, ExtractedFact, NormalizedFact, ValidationFlag,
)
from app.models.document import Document
from app.models.page import Page
from app.schemas.common import PaginatedResponse
from app.schemas.review import (
    AuditLogItemOut, AuditLogListResponse,
    FlagAcceptRequest, FlagCorrectRequest, FlagRejectRequest,
    ConflictResolveRequest, ReviewActionResponse,
)
from app.services.review.review_service import (
    accept_flag, correct_flag, reject_flag, resolve_conflict, list_audit_log,
    VALID_RESOLUTIONS,
)

router = APIRouter(prefix="/review", tags=["Human Verification Console"])


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

@router.get("/flags", response_model=PaginatedResponse)
async def list_flags(
    flag_type:   Optional[str]       = Query(None),
    severity:    Optional[str]       = Query(None),
    status:      Optional[str]       = Query(None),
    document_id: Optional[uuid.UUID] = Query(None),
    page:        int                 = Query(1, ge=1),
    page_size:   int                 = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List validation flags with filtering. Defaults to open flags."""
    filters = []
    if flag_type:
        filters.append(ValidationFlag.flag_type == flag_type)
    if severity:
        filters.append(ValidationFlag.severity == severity)
    if status:
        filters.append(ValidationFlag.status == status)
    else:
        filters.append(ValidationFlag.status == "open")
    if document_id:
        filters.append(
            ValidationFlag.normalized_fact_id.in_(
                select(NormalizedFact.id)
                .join(ExtractedFact, ExtractedFact.id == NormalizedFact.extracted_fact_id)
                .where(ExtractedFact.document_id == document_id)
            )
        )

    total = (await db.execute(
        select(func.count()).select_from(ValidationFlag).where(*filters)
    )).scalar_one()

    flags = (await db.execute(
        select(ValidationFlag)
        .where(*filters)
        .order_by(ValidationFlag.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = []
    for f in flags:
        nf = (await db.execute(select(NormalizedFact).where(NormalizedFact.id == f.normalized_fact_id))).scalar_one_or_none()
        ef = None
        if nf:
            ef = (await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))).scalar_one_or_none()
        entity_name = None
        if nf and nf.canonical_entity_id:
            ent = (await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == nf.canonical_entity_id))).scalar_one_or_none()
            entity_name = ent.canonical_name if ent else None
        items.append({
            "id":                    str(f.id),
            "flag_type":             f.flag_type,
            "severity":              f.severity,
            "status":                f.status,
            "detail":                f.detail,
            "detected_at":           f.detected_at.isoformat(),
            "normalized_fact_id":    str(f.normalized_fact_id),
            "metric":                nf.metric if nf else None,
            "normalized_value":      nf.normalized_value if nf else None,
            "normalized_unit":       nf.normalized_unit if nf else None,
            "entity_name":           entity_name,
            "document_id":           str(ef.document_id) if ef else None,
            "available_actions":     ["accept", "correct", "reject"],
        })

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/flags/{flag_id}/accept", response_model=ReviewActionResponse)
async def flag_accept(
    flag_id: uuid.UUID,
    req: FlagAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await accept_flag(db=db, flag_id=flag_id, reviewer=req.reviewer, note=req.note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ReviewActionResponse(
        status="accepted", action_type="accept", target_id=flag_id,
        audit_log_id=entry.id, message="Flag accepted. Underlying value unchanged.",
    )


@router.post("/flags/{flag_id}/correct", response_model=ReviewActionResponse)
async def flag_correct(
    flag_id: uuid.UUID,
    req: FlagCorrectRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await correct_flag(
            db=db, flag_id=flag_id,
            corrected_value=req.corrected_value,
            corrected_unit=req.corrected_unit,
            reviewer=req.reviewer,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ReviewActionResponse(
        status="corrected", action_type="correct", target_id=flag_id,
        audit_log_id=entry.id,
        message=f"Normalized fact corrected to {req.corrected_value} {req.corrected_unit or ''}.",
    )


@router.post("/flags/{flag_id}/reject", response_model=ReviewActionResponse)
async def flag_reject(
    flag_id: uuid.UUID,
    req: FlagRejectRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await reject_flag(db=db, flag_id=flag_id, reviewer=req.reviewer, note=req.note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ReviewActionResponse(
        status="rejected", action_type="reject", target_id=flag_id,
        audit_log_id=entry.id,
        message="Fact marked as invalid. Retained in DB for audit; excluded from active pipeline.",
    )


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

@router.get("/conflicts", response_model=PaginatedResponse)
async def list_conflicts_review(
    entity_id: Optional[uuid.UUID] = Query(None),
    metric:    Optional[str]       = Query(None),
    status:    Optional[str]       = Query(None, pattern="^(open|resolved|all)$"),
    page:      int                 = Query(1, ge=1),
    page_size: int                 = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List conflicts with resolution action links."""
    filters = []
    if entity_id:
        filters.append(Conflict.canonical_entity_id == entity_id)
    if metric:
        filters.append(Conflict.metric == metric)
    if status and status != "all":
        filters.append(Conflict.status == status)
    elif not status:
        filters.append(Conflict.status == "open")

    total = (await db.execute(
        select(func.count()).select_from(Conflict).where(*filters)
    )).scalar_one()

    conflicts = (await db.execute(
        select(Conflict)
        .where(*filters)
        .order_by(Conflict.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = []
    for c in conflicts:
        entity_name = None
        if c.canonical_entity_id:
            ent = (await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == c.canonical_entity_id))).scalar_one_or_none()
            entity_name = ent.canonical_name if ent else None
        period = f"{c.period_start} → {c.period_end}" if c.period_start else None
        items.append({
            "id":               str(c.id),
            "entity_name":      entity_name,
            "metric":           c.metric,
            "period":           period,
            "value_a":          c.value_a,
            "unit_a":           c.unit_a,
            "value_b":          c.value_b,
            "unit_b":           c.unit_b,
            "delta_pct":        c.delta_pct,
            "status":           c.status,
            "detected_at":      c.detected_at.isoformat(),
            "available_actions": ["resolve"] if c.status == "open" else [],
            "valid_resolutions": sorted(VALID_RESOLUTIONS),
        })

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/conflicts/{conflict_id}/resolve", response_model=ReviewActionResponse)
async def conflict_resolve(
    conflict_id: uuid.UUID,
    req: ConflictResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await resolve_conflict(
            db=db,
            conflict_id=conflict_id,
            resolution=req.resolution,
            canonical_value=req.canonical_value,
            canonical_unit=req.canonical_unit,
            reviewer=req.reviewer,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ReviewActionResponse(
        status="resolved", action_type="resolve_conflict", target_id=conflict_id,
        audit_log_id=entry.id,
        message=f"Conflict resolved: {req.resolution}. Audit log entry created.",
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@router.get("/audit-log", response_model=AuditLogListResponse)
async def audit_log_list(
    action_type: Optional[str]       = Query(None),
    reviewer:    Optional[str]       = Query(None),
    target_id:   Optional[uuid.UUID] = Query(None),
    page:        int                 = Query(1, ge=1),
    page_size:   int                 = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    entries, total = await list_audit_log(
        db=db, action_type=action_type, reviewer=reviewer,
        target_id=target_id, page=page, page_size=page_size,
    )
    items = [
        AuditLogItemOut(
            id=e.id,
            timestamp=e.timestamp,
            reviewer=e.reviewer,
            action_type=e.action_type,
            target_table=e.target_table,
            target_id=e.target_id,
            before_value=e.before_value,
            after_value=e.after_value,
            note=e.note,
        )
        for e in entries
    ]
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)
