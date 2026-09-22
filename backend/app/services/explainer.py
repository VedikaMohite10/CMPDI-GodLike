"""Explainable AI Packaging Module.

Single function: package_response() wraps any analytics or query result into the
standard ExplainableAIResponse envelope, computing the deterministic confidence score.

CONFIDENCE FORMULA (from design doc):
  confidence = round(
      0.35 * extraction_score
    + 0.30 * cross_validation_score
    + 0.20 * reasoning_bonus
    + 0.15 * coverage_score
  ) * 100

Where:
  extraction_score      = avg extraction_confidence of facts used;
                          facts flagged low_confidence are penalised × 0.6.
  cross_validation_score = 1.0 if no open conflict, 0.3 if open conflict, 0.7 if resolved.
  reasoning_bonus       = 1.0 doc-supported | 0.6 data-derived | 0.3 model-inference | 0.0 insuff.
  coverage_score        = tasks_with_results / total_tasks_planned

This module has NO LLM calls and NO side effects — it is a pure transformation function.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import Conflict, ExtractedFact, NormalizedFact, ValidationFlag
from app.schemas.query import (
    ConflictSurfaced,
    EvidenceItem,
    ExplainableAIResponse,
    ReasoningType,
)
from sqlalchemy import and_, select

logger = logging.getLogger(__name__)

# Confidence weights (must sum to 1.0)
_W_EXTRACTION      = 0.35
_W_CROSS_VALIDATION = 0.30
_W_REASONING       = 0.20
_W_COVERAGE        = 0.15

_REASONING_BONUSES: Dict[str, float] = {
    "document-supported":  1.0,
    "data-derived":        0.6,
    "model-inference":     0.3,
    "insufficient-evidence": 0.0,
}

_LOW_CONF_PENALTY = 0.6   # multiply extraction_confidence by this if fact is low-confidence flagged


async def package_response(
    *,
    db: AsyncSession,
    query_id: uuid.UUID,
    question: str,
    answer: str,
    fact_ids: List[uuid.UUID],
    conflicts: List[Conflict],
    reasoning_type: ReasoningType,
    calculation: Optional[str] = None,
    analytics_results: Optional[Dict[str, Any]] = None,
    # Coverage inputs: how many analytics sub-tasks were planned vs. returned results
    tasks_planned: int = 0,
    tasks_with_results: int = 0,
) -> ExplainableAIResponse:
    """Build and return a fully-packaged ExplainableAIResponse.

    Args:
        db:                  Async SQLAlchemy session (for loading fact evidence).
        query_id:            UUID for the response record.
        question:            Original user question.
        answer:              NL answer string (from synthesis LLM or canned template).
        fact_ids:            All normalized_fact IDs used in the answer.
        conflicts:           Open Conflict ORM objects to surface in the response.
        reasoning_type:      Classification of how the answer was derived.
        calculation:         Human-readable formula/method description.
        analytics_results:   Raw analytics structured data (optional).
        tasks_planned:       Total analytics sub-tasks planned.
        tasks_with_results:  Sub-tasks that returned ≥1 result.
    """
    # 1. Load fact evidence
    evidence_items, extraction_scores, cross_validation_scores = await _build_evidence(
        db, fact_ids, conflicts
    )

    # 2. Compute confidence
    confidence = _compute_confidence(
        extraction_scores=extraction_scores,
        cross_validation_scores=cross_validation_scores,
        reasoning_type=reasoning_type,
        tasks_planned=tasks_planned,
        tasks_with_results=tasks_with_results,
    )

    # 3. Build conflict items
    conflict_items = _build_conflict_items(conflicts)

    return ExplainableAIResponse(
        query_id=query_id,
        question=question,
        answer=answer,
        evidence=evidence_items,
        conflicts_surfaced=conflict_items,
        calculation=calculation,
        confidence=confidence,
        reasoning_type=reasoning_type,
        analytics_results=analytics_results,
        created_at=datetime.now(timezone.utc),
    )


def _compute_confidence(
    extraction_scores: List[float],
    cross_validation_scores: List[float],
    reasoning_type: str,
    tasks_planned: int,
    tasks_with_results: int,
) -> int:
    """Deterministic confidence score [0–100].

    All four components are observable data signals — no LLM self-reporting.
    """
    # extraction_score: average of (penalised) extraction confidences
    if extraction_scores:
        extraction_score = sum(extraction_scores) / len(extraction_scores)
    else:
        extraction_score = 0.5  # neutral if no extraction confidence recorded

    # cross_validation_score: average conflict penalty across facts
    if cross_validation_scores:
        cross_validation_score = sum(cross_validation_scores) / len(cross_validation_scores)
    else:
        cross_validation_score = 1.0  # no facts → no conflicts → full score

    # reasoning_bonus
    reasoning_bonus = _REASONING_BONUSES.get(reasoning_type, 0.0)

    # coverage_score
    if tasks_planned == 0:
        coverage_score = 1.0  # semantic-only query: score based on evidence presence
        if not extraction_scores:
            coverage_score = 0.0
    else:
        coverage_score = tasks_with_results / tasks_planned

    raw = (
        _W_EXTRACTION       * extraction_score
        + _W_CROSS_VALIDATION * cross_validation_score
        + _W_REASONING        * reasoning_bonus
        + _W_COVERAGE         * coverage_score
    )
    return max(0, min(100, round(raw * 100)))


async def _build_evidence(
    db: AsyncSession,
    fact_ids: List[uuid.UUID],
    conflicts: List[Conflict],
) -> tuple[List[EvidenceItem], List[float], List[float]]:
    """Load evidence data for each fact.

    Returns (evidence_items, extraction_scores, cross_validation_scores).
    extraction_scores and cross_validation_scores are parallel lists used for confidence.
    """
    if not fact_ids:
        return [], [], []

    conflict_fact_ids = set()
    for c in conflicts:
        if c.status == "open":
            conflict_fact_ids.add(c.fact_a_id)
            conflict_fact_ids.add(c.fact_b_id)

    evidence_items: List[EvidenceItem] = []
    extraction_scores: List[float] = []
    cross_validation_scores: List[float] = []

    # Deduplicate fact_ids while preserving order
    seen: set[uuid.UUID] = set()
    unique_ids = [fid for fid in fact_ids if not (fid in seen or seen.add(fid))]  # type: ignore

    for fact_id in unique_ids:
        try:
            item, ext_score, cv_score = await _load_fact_evidence(
                db, fact_id, conflict_fact_ids
            )
            evidence_items.append(item)
            extraction_scores.append(ext_score)
            cross_validation_scores.append(cv_score)
        except Exception as exc:
            logger.warning("Could not load evidence for fact %s: %s", fact_id, exc)

    return evidence_items, extraction_scores, cross_validation_scores


async def _load_fact_evidence(
    db: AsyncSession,
    fact_id: uuid.UUID,
    conflict_fact_ids: set[uuid.UUID],
) -> tuple[EvidenceItem, float, float]:
    """Load a single fact's full evidence chain."""
    from app.models.document import Document
    from app.models.extraction import ExtractedTable, ExtractedTextBlock
    from app.models.page import Page

    nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == fact_id))
    nf = nf_res.scalar_one_or_none()
    if nf is None:
        raise ValueError(f"NormalizedFact {fact_id} not found")

    ef_res = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))
    ef = ef_res.scalar_one()

    pg_res = await db.execute(select(Page).where(Page.id == ef.page_id))
    pg = pg_res.scalar_one()

    doc_res = await db.execute(select(Document).where(Document.id == ef.document_id))
    doc = doc_res.scalar_one()

    # Determine excerpt and source_type
    excerpt = ""
    source_type = "unknown"
    if ef.table_id:
        source_type = "table"
        t_res = await db.execute(
            select(ExtractedTable).where(ExtractedTable.id == ef.table_id)
        )
        t = t_res.scalar_one_or_none()
        if t:
            excerpt = f"Table: {t.caption or '(no caption)'} | Row value: {ef.raw_value}"
    elif ef.block_id:
        source_type = "block"
        b_res = await db.execute(
            select(ExtractedTextBlock).where(ExtractedTextBlock.id == ef.block_id)
        )
        b = b_res.scalar_one_or_none()
        if b:
            excerpt = (b.text or "")[:500]

    # Fallback excerpt from raw value
    if not excerpt:
        excerpt = f"{ef.raw_entity_text or ''} {ef.raw_metric_text or ''}: {ef.raw_value}"

    # Extraction score — penalise low-confidence flagged facts
    raw_conf = ef.extraction_confidence or 0.5
    flags_res = await db.execute(
        select(ValidationFlag).where(
            and_(
                ValidationFlag.normalized_fact_id == fact_id,
                ValidationFlag.flag_type == "low_confidence",
                ValidationFlag.status == "open",
            )
        )
    )
    is_low_conf = flags_res.scalar_one_or_none() is not None
    ext_score = raw_conf * (_LOW_CONF_PENALTY if is_low_conf else 1.0)

    # Cross-validation score
    cv_score = 0.3 if fact_id in conflict_fact_ids else 1.0

    evidence_item = EvidenceItem(
        fact_id=fact_id,
        document_id=doc.id,
        document_filename=doc.original_filename or doc.filename,
        page_number=pg.page_number,
        excerpt=excerpt,
        source_type=source_type,
        extraction_confidence=ef.extraction_confidence,
    )
    return evidence_item, ext_score, cv_score


def _build_conflict_items(conflicts: List[Conflict]) -> List[ConflictSurfaced]:
    """Convert Conflict ORM objects to ConflictSurfaced schema items."""
    items = []
    for c in conflicts:
        desc_parts = [f"Conflicting values for same entity/metric/period:"]
        if c.value_a is not None and c.value_b is not None:
            unit_a = c.unit_a or ""
            unit_b = c.unit_b or ""
            desc_parts.append(
                f"{c.value_a} {unit_a} vs {c.value_b} {unit_b}"
            )
            if c.delta_pct is not None:
                desc_parts.append(f"(delta: {c.delta_pct:.1f}%)")
        description = " ".join(desc_parts)

        items.append(ConflictSurfaced(
            conflict_id=c.id,
            fact_a_id=c.fact_a_id,
            fact_b_id=c.fact_b_id,
            description=description,
            delta_pct=c.delta_pct,
            status=c.status,
        ))
    return items
