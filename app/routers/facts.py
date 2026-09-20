"""Facts router — GET /facts, GET /facts/{id}/evidence."""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2 import (
    NormalizedFact, ExtractedFact, ValidationFlag, Conflict,
    CanonicalEntity, EntityAlias,
)
from app.models.extraction import ExtractedTable, ExtractedTextBlock
from app.models.page import Page
from app.models.document import Document
from app.schemas.common import PaginatedResponse
from app.schemas.facts import NormalizedFactSummary, FactEvidenceResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facts", tags=["facts"])


@router.get("", response_model=PaginatedResponse)
async def list_facts(
    entity_id:   Optional[uuid.UUID] = Query(None),
    metric:      Optional[str]        = Query(None),
    period_year: Optional[int]        = Query(None),
    document_id: Optional[uuid.UUID]  = Query(None),
    flag_type:   Optional[str]        = Query(None),
    page:        int                  = Query(1, ge=1),
    page_size:   int                  = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List normalized facts with optional filters."""
    filters = [NormalizedFact.fact_processing_status != "failed"]

    if entity_id:
        filters.append(NormalizedFact.canonical_entity_id == entity_id)
    if metric:
        filters.append(NormalizedFact.metric == metric)
    if period_year:
        filters.append(
            and_(
                func.extract("year", NormalizedFact.period_start) <= period_year,
                func.extract("year", NormalizedFact.period_end)   >= period_year,
            )
        )
    if document_id:
        filters.append(
            NormalizedFact.extracted_fact_id.in_(
                select(ExtractedFact.id).where(ExtractedFact.document_id == document_id)
            )
        )
    if flag_type:
        filters.append(
            exists(
                select(ValidationFlag.id).where(
                    and_(
                        ValidationFlag.normalized_fact_id == NormalizedFact.id,
                        ValidationFlag.flag_type == flag_type,
                    )
                )
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(NormalizedFact).where(*filters)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(NormalizedFact)
        .where(*filters)
        .order_by(NormalizedFact.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    nfacts = result.scalars().all()

    items = []
    for nf in nfacts:
        # Fetch joined data
        ef_res  = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))
        ef      = ef_res.scalar_one_or_none()
        doc_res = await db.execute(select(Document).where(Document.id == ef.document_id)) if ef else None
        doc     = doc_res.scalar_one_or_none() if doc_res else None
        page_res = await db.execute(select(Page).where(Page.id == ef.page_id)) if ef else None
        pg       = page_res.scalar_one_or_none() if page_res else None
        entity_name = None
        if nf.canonical_entity_id:
            ent_res = await db.execute(select(CanonicalEntity).where(CanonicalEntity.id == nf.canonical_entity_id))
            ent = ent_res.scalar_one_or_none()
            entity_name = ent.canonical_name if ent else None

        flag_count_res = await db.execute(
            select(func.count()).select_from(ValidationFlag)
            .where(ValidationFlag.normalized_fact_id == nf.id)
        )
        flag_count = flag_count_res.scalar_one()

        conflict_exists_res = await db.execute(
            select(func.count()).select_from(Conflict).where(
                (Conflict.fact_a_id == nf.id) | (Conflict.fact_b_id == nf.id)
            )
        )
        has_conflict = conflict_exists_res.scalar_one() > 0

        items.append(NormalizedFactSummary(
            id                       = nf.id,
            metric                   = nf.metric,
            normalized_value         = nf.normalized_value,
            normalized_unit          = nf.normalized_unit,
            period_label             = nf.period_label,
            entity_resolution_method = nf.entity_resolution_method,
            fact_processing_status   = nf.fact_processing_status,
            canonical_entity_name    = entity_name,
            flag_count               = flag_count,
            has_conflict             = has_conflict,
            document_id              = ef.document_id if ef else None,
            document_filename        = doc.original_filename if doc else None,
            page_number              = pg.page_number if pg else None,
            extraction_confidence    = ef.extraction_confidence if ef else None,
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{fact_id}/evidence")
async def get_fact_evidence(fact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Full lineage chain for one normalized fact."""
    nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == fact_id))
    nf = nf_res.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="Fact not found.")

    ef_res = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))
    ef = ef_res.scalar_one()

    pg_res  = await db.execute(select(Page).where(Page.id == ef.page_id))
    pg      = pg_res.scalar_one()
    doc_res = await db.execute(select(Document).where(Document.id == ef.document_id))
    doc     = doc_res.scalar_one()

    # Source: table or block
    source = {}
    if ef.table_id:
        t_res = await db.execute(select(ExtractedTable).where(ExtractedTable.id == ef.table_id))
        t = t_res.scalar_one_or_none()
        source = {
            "type": "table",
            "table": {"id": str(t.id), "caption": t.caption,
                      "raw_structure": t.raw_structure, "position": t.position} if t else None,
            "block": None,
        }
    elif ef.block_id:
        b_res = await db.execute(select(ExtractedTextBlock).where(ExtractedTextBlock.id == ef.block_id))
        b = b_res.scalar_one_or_none()
        source = {
            "type": "block",
            "table": None,
            "block": {"id": str(b.id), "text": b.text, "block_type": b.block_type,
                      "position": b.position} if b else None,
        }

    # Flags
    flags_res = await db.execute(
        select(ValidationFlag).where(ValidationFlag.normalized_fact_id == nf.id)
    )
    flags = [
        {"id": str(f.id), "flag_type": f.flag_type, "severity": f.severity,
         "detail": f.detail, "status": f.status, "detected_at": f.detected_at.isoformat()}
        for f in flags_res.scalars().all()
    ]

    # Entity + aliases
    entity_out = None
    if nf.canonical_entity_id:
        ent_res = await db.execute(
            select(CanonicalEntity).where(CanonicalEntity.id == nf.canonical_entity_id)
        )
        ent = ent_res.scalar_one_or_none()
        if ent:
            alias_res = await db.execute(
                select(EntityAlias).where(EntityAlias.canonical_entity_id == ent.id)
            )
            entity_out = {
                "id": str(ent.id),
                "canonical_name": ent.canonical_name,
                "entity_type": ent.entity_type,
                "aliases": [
                    {"alias_text": a.alias_text, "resolution_method": a.resolution_method,
                     "confidence": a.confidence}
                    for a in alias_res.scalars().all()
                ],
            }

    return {
        "fact": {
            "id": str(nf.id),
            "metric": nf.metric,
            "metric_category": nf.metric_category,
            "normalized_value": nf.normalized_value,
            "normalized_unit": nf.normalized_unit,
            "original_value_text": nf.original_value_text,
            "original_unit_text": nf.original_unit_text,
            "period_start": nf.period_start.isoformat() if nf.period_start else None,
            "period_end":   nf.period_end.isoformat()   if nf.period_end   else None,
            "period_label": nf.period_label,
            "date_parse_method": nf.date_parse_method,
            "entity_resolution_method": nf.entity_resolution_method,
            "entity_resolution_confidence": nf.entity_resolution_confidence,
            "normalization_notes": nf.normalization_notes,
            "fact_processing_status": nf.fact_processing_status,
        },
        "extracted": {
            "id": str(ef.id),
            "raw_entity_text": ef.raw_entity_text,
            "raw_metric_text": ef.raw_metric_text,
            "raw_value": ef.raw_value,
            "raw_unit_text": ef.raw_unit_text,
            "raw_date_text": ef.raw_date_text,
            "extraction_method": ef.extraction_method,
            "extraction_model": ef.extraction_model,
            "extraction_confidence": ef.extraction_confidence,
            "llm_raw_output": ef.llm_raw_output,
        },
        "source": source,
        "page": {"page_id": str(pg.id), "page_number": pg.page_number},
        "document": {
            "id": str(doc.id),
            "filename": doc.filename,
            "original_filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "upload_date": doc.upload_date.isoformat(),
            "report_date": doc.report_date.isoformat() if doc.report_date else None,
        },
        "flags":  flags,
        "entity": entity_out,
    }
