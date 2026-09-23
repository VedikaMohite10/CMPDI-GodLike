"""Duplicates router — GET /duplicates."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase2 import DuplicateCandidate, NormalizedFact, CanonicalEntity
from app.models.document import Document
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.get("", response_model=PaginatedResponse)
async def list_duplicates(
    scope:     Optional[str] = Query(None, pattern="^(document|fact|all)$"),
    status:    Optional[str] = Query(None, pattern="^(open|all)$"),
    page:      int            = Query(1, ge=1),
    page_size: int            = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = []
    if scope and scope != "all":
        filters.append(DuplicateCandidate.scope == scope)
    if status and status != "all":
        filters.append(DuplicateCandidate.status == status)
    elif not status:
        filters.append(DuplicateCandidate.status == "open")

    total_res = await db.execute(
        select(func.count()).select_from(DuplicateCandidate).where(*filters)
    )
    total = total_res.scalar_one()

    result = await db.execute(
        select(DuplicateCandidate)
        .where(*filters)
        .order_by(DuplicateCandidate.similarity_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    dupes = result.scalars().all()

    items = []
    for d in dupes:
        item: dict = {
            "id":               str(d.id),
            "scope":            d.scope,
            "similarity_score": d.similarity_score,
            "detection_method": d.detection_method,
            "status":           d.status,
            "detected_at":      d.detected_at.isoformat(),
            "document_a": None, "document_b": None,
            "fact_a": None,     "fact_b": None,
        }
        if d.scope == "document":
            for attr, key in [("document_id_a", "document_a"), ("document_id_b", "document_b")]:
                doc_id = getattr(d, attr)
                if doc_id:
                    doc_res = await db.execute(select(Document).where(Document.id == doc_id))
                    doc = doc_res.scalar_one_or_none()
                    item[key] = {"id": str(doc.id), "filename": doc.original_filename,
                                 "upload_date": doc.upload_date.isoformat()} if doc else None
        elif d.scope == "fact":
            for attr, key in [("fact_id_a", "fact_a"), ("fact_id_b", "fact_b")]:
                fact_id = getattr(d, attr)
                if fact_id:
                    nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == fact_id))
                    nf = nf_res.scalar_one_or_none()
                    entity_name = None
                    if nf and nf.canonical_entity_id:
                        ent_res = await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == nf.canonical_entity_id))
                        ent = ent_res.scalar_one_or_none()
                        entity_name = ent.canonical_name if ent else None
                    item[key] = {"id": str(nf.id), "metric": nf.metric,
                                 "normalized_value": nf.normalized_value,
                                 "canonical_entity_name": entity_name} if nf else None
        items.append(item)

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
