"""Conflicts router — GET /conflicts, GET /conflicts/{id}."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2 import Conflict, CanonicalEntity, NormalizedFact, ExtractedFact
from app.models.document import Document
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


async def _build_conflict_summary(c: Conflict, db: AsyncSession) -> dict:
    entity_name = None
    if c.canonical_entity_id:
        e_res = await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == c.canonical_entity_id))
        e = e_res.scalar_one_or_none()
        entity_name = e.canonical_name if e else None

    async def doc_filename(fact_id):
        nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == fact_id))
        nf = nf_res.scalar_one_or_none()
        if not nf:
            return None
        ef_res = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))
        ef = ef_res.scalar_one_or_none()
        if not ef:
            return None
        d_res = await db.execute(select(Document).where(Document.id == ef.document_id))
        d = d_res.scalar_one_or_none()
        return d.original_filename if d else None

    fname_a = await doc_filename(c.fact_a_id)
    fname_b = await doc_filename(c.fact_b_id)

    period_label = None
    if c.period_start and c.period_end:
        period_label = f"{c.period_start.isoformat()} → {c.period_end.isoformat()}"

    return {
        "id":                    str(c.id),
        "canonical_entity_name": entity_name,
        "metric":                c.metric,
        "period_label":          period_label,
        "value_a":               c.value_a,
        "unit_a":                c.unit_a,
        "value_b":               c.value_b,
        "unit_b":                c.unit_b,
        "delta_pct":             c.delta_pct,
        "document_a_filename":   fname_a,
        "document_b_filename":   fname_b,
        "status":                c.status,
        "detected_at":           c.detected_at.isoformat(),
    }


@router.get("", response_model=PaginatedResponse)
async def list_conflicts(
    entity_id: Optional[uuid.UUID] = Query(None),
    metric:    Optional[str]        = Query(None),
    status:    Optional[str]        = Query(None, pattern="^(open|resolved|all)$"),
    page:      int                  = Query(1, ge=1),
    page_size: int                  = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if entity_id:
        filters.append(Conflict.canonical_entity_id == entity_id)
    if metric:
        filters.append(Conflict.metric == metric)
    if status and status != "all":
        filters.append(Conflict.status == status)
    elif not status:
        filters.append(Conflict.status == "open")   # default: open only

    total_res = await db.execute(
        select(func.count()).select_from(Conflict).where(*filters)
    )
    total = total_res.scalar_one()

    result = await db.execute(
        select(Conflict)
        .where(*filters)
        .order_by(Conflict.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conflicts = result.scalars().all()
    items = [await _build_conflict_summary(c, db) for c in conflicts]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{conflict_id}")
async def get_conflict(conflict_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Full detail with both facts' complete evidence chains."""
    result = await db.execute(select(Conflict).where(Conflict.id == conflict_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Conflict not found.")

    # Import here to avoid circular import
    from app.routers.facts import get_fact_evidence

    summary = await _build_conflict_summary(c, db)

    try:
        evidence_a = await get_fact_evidence(c.fact_a_id, db)
    except HTTPException:
        evidence_a = None

    try:
        evidence_b = await get_fact_evidence(c.fact_b_id, db)
    except HTTPException:
        evidence_b = None

    return {
        "conflict":        summary,
        "fact_a_evidence": evidence_a,
        "fact_b_evidence": evidence_b,
    }
