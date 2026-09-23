"""Validation flags router — GET /validation-flags."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase2 import ValidationFlag, NormalizedFact, ExtractedFact, CanonicalEntity
from app.models.page import Page
from app.models.document import Document
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/validation-flags", tags=["validation"])


@router.get("", response_model=PaginatedResponse)
async def list_flags(
    flag_type:   Optional[str]        = Query(None),
    severity:    Optional[str]        = Query(None, pattern="^(info|warning|error)$"),
    status:      Optional[str]        = Query(None, pattern="^(open|acknowledged|all)$"),
    document_id: Optional[uuid.UUID]  = Query(None),
    page:        int                  = Query(1, ge=1),
    page_size:   int                  = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = []
    if flag_type:
        filters.append(ValidationFlag.flag_type == flag_type)
    if severity:
        filters.append(ValidationFlag.severity == severity)
    if status and status != "all":
        filters.append(ValidationFlag.status == status)
    elif not status:
        filters.append(ValidationFlag.status == "open")

    # document_id filter requires joining through normalized_facts → extracted_facts
    if document_id:
        filters.append(
            ValidationFlag.normalized_fact_id.in_(
                select(NormalizedFact.id)
                .join(ExtractedFact, ExtractedFact.id == NormalizedFact.extracted_fact_id)
                .where(ExtractedFact.document_id == document_id)
            )
        )

    total_res = await db.execute(
        select(func.count()).select_from(ValidationFlag).where(*filters)
    )
    total = total_res.scalar_one()

    result = await db.execute(
        select(ValidationFlag)
        .where(*filters)
        .order_by(ValidationFlag.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    flags = result.scalars().all()

    items = []
    for f in flags:
        nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == f.normalized_fact_id))
        nf = nf_res.scalar_one_or_none()
        ef_res = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id)) if nf else None
        ef = ef_res.scalar_one_or_none() if ef_res else None
        doc = pg = entity_name = None
        if ef:
            doc_res = await db.execute(select(Document).where(Document.id == ef.document_id))
            doc = doc_res.scalar_one_or_none()
            pg_res = await db.execute(select(Page).where(Page.id == ef.page_id))
            pg = pg_res.scalar_one_or_none()
        if nf and nf.canonical_entity_id:
            ent_res = await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == nf.canonical_entity_id))
            ent = ent_res.scalar_one_or_none()
            entity_name = ent.canonical_name if ent else None

        items.append({
            "id":                    str(f.id),
            "flag_type":             f.flag_type,
            "severity":              f.severity,
            "detail":                f.detail,
            "status":                f.status,
            "detected_at":           f.detected_at.isoformat(),
            "normalized_fact_id":    str(f.normalized_fact_id),
            "metric":                nf.metric if nf else None,
            "normalized_value":      nf.normalized_value if nf else None,
            "normalized_unit":       nf.normalized_unit if nf else None,
            "canonical_entity_name": entity_name,
            "document_id":           str(ef.document_id) if ef else None,
            "document_filename":     doc.original_filename if doc else None,
            "page_number":           pg.page_number if pg else None,
        })

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
