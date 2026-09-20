"""Top-level Phase 2 fact pipeline orchestrator.

Sequence for a single document:
  1. Mark job as 'extracting' in fact_processing_log
  2. Extract facts from all extracted_tables (LLM) and extracted_text_blocks (heuristic)
  3. Mark job as 'normalizing'
  4. Normalize each extracted fact
  5. Mark job as 'validating'
  6. Run validation checks → insert flags
  7. Run conflict detection for this document's new facts
  8. Run document duplicate detection
  9. Mark job as 'done'

Idempotency: if force=False and a 'done' log entry exists, skip.
If force=True, mark old extracted_facts as obsolete and re-run.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.extraction import ExtractedTable, ExtractedTextBlock, ExtractedImage
from app.models.page import Page
from app.models.phase2 import (
    ExtractedFact, NormalizedFact, ValidationFlag, FactProcessingLog,
)

from app.services.phase2.llm_table_extractor import extract_facts_from_table
from app.services.phase2.heuristic_text_extractor import extract_from_text
from app.services.phase2.normalization_pipeline import normalize_fact
from app.services.phase2.validation_engine import run_all_checks
from app.services.phase2.conflict_detector import detect_conflicts
from app.services.phase2.duplicate_detector import detect_document_duplicates, detect_fact_duplicates

logger = logging.getLogger(__name__)


async def run_phase2_pipeline(
    document_id: uuid.UUID,
    db: AsyncSession,
    force: bool = False,
) -> FactProcessingLog:
    """Run the full Phase 2 pipeline for one document.

    Returns the updated FactProcessingLog record.
    Raises ValueError if document not found or Phase 1 not complete.
    """
    # ── 0. Validate document ─────────────────────────────────────────────
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found.")
    if doc.processing_status != "done":
        raise ValueError(
            f"Document {document_id} has Phase 1 status '{doc.processing_status}' "
            "— Phase 2 requires status='done'."
        )

    # ── 1. Idempotency check / force mode ────────────────────────────────
    log_result = await db.execute(
        select(FactProcessingLog).where(
            and_(FactProcessingLog.document_id == document_id,
                 FactProcessingLog.phase == "phase2")
        )
    )
    job = log_result.scalar_one_or_none()

    if job and job.status == "done" and not force:
        logger.info("Document %s already has Phase 2 'done' log — skipping.", document_id)
        return job

    if job and force:
        # Mark existing extracted_facts as obsolete (preserves audit trail)
        await db.execute(
            update(ExtractedFact)
            .where(
                and_(ExtractedFact.document_id == document_id,
                     ExtractedFact.is_obsolete.is_(False))
            )
            .values(is_obsolete=True)
        )
        job.status = "queued"
        job.facts_extracted  = 0
        job.facts_normalized = 0
        job.facts_flagged    = 0
        job.conflicts_found  = 0
        job.error            = None
        job.started_at       = None
        job.completed_at     = None
    elif not job:
        job = FactProcessingLog(
            document_id=document_id,
            phase="phase2",
            status="queued",
        )
        db.add(job)
        await db.flush()

    # ── 2. Extraction ─────────────────────────────────────────────────────
    job.status     = "extracting"
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    extracted_facts: list[ExtractedFact] = []

    try:
        # --- Tables (LLM) ------------------------------------------------
        tables_result = await db.execute(
            select(ExtractedTable, Page)
            .join(Page, Page.id == ExtractedTable.page_id)
            .where(ExtractedTable.document_id == document_id)
            .order_by(Page.page_number, ExtractedTable.table_index)
        )
        table_rows = tables_result.all()

        for table, page in table_rows:
            raw = table.raw_structure or {}
            headers = raw.get("headers", [])
            rows    = raw.get("rows", [])
            caption = table.caption or ""

            # Find surrounding text context from the same page
            ctx_result = await db.execute(
                select(ExtractedTextBlock.text)
                .where(
                    and_(ExtractedTextBlock.page_id == page.id,
                         ExtractedTextBlock.document_id == document_id)
                )
                .limit(2)
            )
            context = " ".join(r[0] for r in ctx_result.all())

            fact_items, llm_raw, skipped = await extract_facts_from_table(
                caption=caption,
                context=context,
                headers=headers,
                rows=rows,
                table_id=str(table.id),
            )

            if skipped or not fact_items:
                # Even if skipped, store one fact with low confidence for audit
                if llm_raw.get("table_skipped"):
                    ef = ExtractedFact(
                        document_id         = document_id,
                        page_id             = page.id,
                        table_id            = table.id,
                        raw_value           = "(table skipped)",
                        extraction_method   = "llm_table",
                        extraction_model    = _fact_model(),
                        llm_raw_output      = llm_raw,
                        extraction_confidence = 0.0,
                        is_obsolete         = False,
                    )
                    db.add(ef)
                continue

            # Build date_text from caption or surrounding context
            date_text = _extract_date_hint(caption + " " + context)

            for item in fact_items:
                # Map LLM row_index → which header(s) are numeric
                ef = ExtractedFact(
                    document_id           = document_id,
                    page_id               = page.id,
                    table_id              = table.id,
                    raw_entity_text       = item.entity_text,
                    raw_metric_text       = item.metric_text,
                    raw_value             = item.value_text,
                    raw_unit_text         = item.unit_text,
                    raw_date_text         = item.date_text or date_text,
                    extraction_method     = "llm_table",
                    extraction_model      = _fact_model(),
                    llm_raw_output        = llm_raw,
                    extraction_confidence = item.confidence,
                    is_obsolete           = False,
                )
                db.add(ef)
                extracted_facts.append(ef)

        # --- Text blocks (heuristic) -------------------------------------
        blocks_result = await db.execute(
            select(ExtractedTextBlock, Page)
            .join(Page, Page.id == ExtractedTextBlock.page_id)
            .where(ExtractedTextBlock.document_id == document_id)
            .order_by(Page.page_number, ExtractedTextBlock.block_index)
        )
        block_rows = blocks_result.all()

        for block, page in block_rows:
            date_text = _extract_date_hint(block.text)
            raw_facts = extract_from_text(
                text=block.text,
                entity_text=None,
                date_text=date_text,
            )
            for rf in raw_facts:
                ef = ExtractedFact(
                    document_id           = document_id,
                    page_id               = page.id,
                    block_id              = block.id,
                    raw_entity_text       = rf["raw_entity_text"],
                    raw_metric_text       = rf["raw_metric_text"],
                    raw_value             = rf["raw_value"],
                    raw_unit_text         = rf["raw_unit_text"],
                    raw_date_text         = rf["raw_date_text"],
                    extraction_method     = "heuristic_text",
                    extraction_model      = None,
                    llm_raw_output        = None,
                    extraction_confidence = rf["extraction_confidence"],
                    is_obsolete           = False,
                )
                db.add(ef)
                extracted_facts.append(ef)

        await db.flush()  # get IDs for extracted_facts
        job.facts_extracted = len(extracted_facts)

        # ── 3. Normalization ─────────────────────────────────────────────
        job.status = "normalizing"
        await db.flush()

        normalized_facts: list[NormalizedFact] = []
        for ef in extracted_facts:
            try:
                nf = await normalize_fact(ef, db)
                db.add(nf)
                normalized_facts.append(nf)
            except Exception as exc:
                logger.warning("Normalization failed for extracted_fact %s: %s", ef.id, exc)

        await db.flush()
        job.facts_normalized = len(normalized_facts)

        # ── 4. Validation ─────────────────────────────────────────────────
        job.status = "validating"
        await db.flush()

        total_flags = 0
        for nf in normalized_facts:
            # Eagerly load the extracted_fact relationship for validation checks
            ef_result = await db.execute(
                select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id)
            )
            ef = ef_result.scalar_one()
            nf.extracted_fact = ef   # populate relationship in memory

            flags = await run_all_checks(nf, ef, db)
            for flag in flags:
                db.add(flag)
            total_flags += len(flags)

        await db.flush()
        job.facts_flagged = total_flags

        # ── 5. Conflict + Duplicate detection ─────────────────────────────
        new_conflicts = await detect_conflicts(db, document_id=document_id)
        job.conflicts_found = new_conflicts

        await detect_document_duplicates(document_id, db)
        await detect_fact_duplicates(document_id, db)

        # ── 6. Done ───────────────────────────────────────────────────────
        job.status       = "done"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(
            "Phase 2 pipeline done for doc %s: %d extracted, %d normalized, %d flags, %d conflicts.",
            document_id, job.facts_extracted, job.facts_normalized,
            job.facts_flagged, job.conflicts_found,
        )

    except Exception as exc:
        logger.exception("Phase 2 pipeline failed for doc %s: %s", document_id, exc)
        job.status = "failed"
        job.error  = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()

    return job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fact_model() -> str:
    from app.config import get_settings
    return get_settings().FACT_LLM_MODEL


import re as _re
_DATE_HINT_RE = _re.compile(
    r"(?:FY\s*)?\d{4}[-/]\d{2,4}|Q[1-4]\s*\d{4}|\d{4}-\d{2}-\d{2}|\d{4}",
    _re.IGNORECASE,
)

def _extract_date_hint(text: str) -> str | None:
    """Extract the first plausible date/period string from text."""
    m = _DATE_HINT_RE.search(text or "")
    return m.group(0) if m else None
