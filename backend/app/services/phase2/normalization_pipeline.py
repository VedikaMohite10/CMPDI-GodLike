"""Normalization pipeline — orchestrates unit, date, and entity resolution.

Produces a NormalizedFact row from one ExtractedFact row.
All steps are deterministic except entity_resolver (which may call bge-m3).
"""
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import ExtractedFact, NormalizedFact
from app.services.phase2.metric_registry import resolve_metric
from app.services.phase2.unit_normalizer import normalize_unit
from app.services.phase2.date_normalizer import parse_date
from app.services.phase2.entity_resolver import resolve_entity

logger = logging.getLogger(__name__)


async def normalize_fact(ef: ExtractedFact, db: AsyncSession) -> NormalizedFact:
    """Create and return an un-persisted NormalizedFact for the given ExtractedFact.

    The caller is responsible for adding it to the session and committing.
    """
    notes: dict = {}

    # ── 1. Metric resolution ─────────────────────────────────────────────
    metric = resolve_metric(ef.raw_metric_text or "")
    if metric is None and ef.raw_metric_text:
        notes["metric_unresolved"] = ef.raw_metric_text
    from app.services.phase2.metric_registry import METRIC_CATEGORY
    metric_category = METRIC_CATEGORY.get(metric) if metric else None

    # ── 2. Unit + value normalization ────────────────────────────────────
    norm_value, norm_unit, conv_note, unit_notes = normalize_unit(
        ef.raw_value or "", ef.raw_unit_text
    )
    notes.update(unit_notes)
    if conv_note:
        notes["unit_conversion"] = conv_note

    # ── 3. Date / period parsing ─────────────────────────────────────────
    period_start, period_end, period_label, date_method = parse_date(ef.raw_date_text or "")
    if date_method == "unresolved" and ef.raw_date_text:
        notes["date_unresolved"] = ef.raw_date_text

    # ── 4. Entity resolution ──────────────────────────────────────────────
    entity_id: Optional[uuid.UUID] = None
    entity_method = "unresolved"
    entity_conf   = 0.0
    try:
        entity_id, entity_method, entity_conf = await resolve_entity(
            ef.raw_entity_text or "", db
        )
        if entity_method != "unresolved":
            notes["entity_alias"] = ef.raw_entity_text
    except Exception as exc:
        logger.warning("Entity resolution failed for fact %s: %s", ef.id, exc)
        notes["entity_resolution_error"] = str(exc)

    # ── 5. Determine processing status ───────────────────────────────────
    status = "normalized"
    if norm_value is None:
        status = "partial"
    elif entity_method == "unresolved" or metric is None:
        status = "partial"

    return NormalizedFact(
        extracted_fact_id             = ef.id,
        canonical_entity_id           = entity_id,
        entity_resolution_method      = entity_method,
        entity_resolution_confidence  = entity_conf,
        metric                        = metric,
        metric_category               = metric_category,
        normalized_value              = norm_value,
        normalized_unit               = norm_unit,
        original_value_text           = ef.raw_value,
        original_unit_text            = ef.raw_unit_text,
        period_start                  = period_start,
        period_end                    = period_end,
        period_label                  = period_label or ef.raw_date_text,
        date_parse_method             = date_method,
        normalization_notes           = notes if notes else None,
        fact_processing_status        = status,
    )
