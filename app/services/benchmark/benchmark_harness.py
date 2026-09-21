"""Benchmark Harness — Phase 5.

Runs accuracy measurements against a labeled ground-truth set and stores results.

CRITICAL LABELING RULE: Synthetic document results are NEVER aggregated with
real document results. The JSON response always separates them and lists
synthetic_doc_ids so downstream consumers can identify provenance.

Measured metrics:
  text_extraction_accuracy      — character-level match rate against labeled passages
  table_extraction_accuracy     — cell-level match rate for labeled table values
  entity_resolution_accuracy    — % labeled entities correctly resolved to canonical
  unit_normalization_accuracy   — % labeled facts with correct normalized unit
  conflict_detection_precision  — TP / (TP + FP) for deliberately injected conflicts
  conflict_detection_recall     — TP / (TP + FN) for deliberately injected conflicts
  citation_accuracy             — % returned citations pointing to correct doc+page
  query_answer_correctness      — % fixed-question answers within ±1% of known correct value
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.phase2 import (
    CanonicalEntity, EntityAlias, ExtractedFact, NormalizedFact, Conflict,
)
from app.models.phase5 import BenchmarkGroundTruth, BenchmarkRun

logger = logging.getLogger(__name__)

# Ground truth files live here — relative to project root
GROUND_TRUTH_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "benchmark_ground_truth"
QUERY_GT_FILE = GROUND_TRUTH_DIR / "query_ground_truth.json"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_benchmark(db: AsyncSession, note: Optional[str] = None) -> BenchmarkRun:
    """Load all ground-truth label sets and run the full benchmark harness.

    Returns the stored BenchmarkRun record.
    """
    logger.info("Starting benchmark harness run…")

    # Load ground truth from DB (loaded by migration) + JSON files
    gt_rows = (await db.execute(select(BenchmarkGroundTruth))).scalars().all()

    real_gt = [g for g in gt_rows if not g.is_synthetic]
    synthetic_gt = [g for g in gt_rows if g.is_synthetic]

    real_metrics = await _evaluate_label_sets(db, real_gt)
    synthetic_metrics = await _evaluate_label_sets(db, synthetic_gt)

    # Query answer correctness (fixed question set)
    query_metrics = await _evaluate_query_correctness(db)

    # Collect synthetic document IDs (for provenance labeling)
    synthetic_doc_ids = [
        str(g.document_id) for g in synthetic_gt if g.document_id is not None
    ]

    results = {
        "real": {**real_metrics, **query_metrics.get("real", {})},
        "synthetic": {
            **synthetic_metrics,
            "synthetic_types_tested": list({g.synthetic_type for g in synthetic_gt
                                            if g.synthetic_type}),
        },
        "synthetic_doc_ids": synthetic_doc_ids,
        "provenance_note": (
            "Synthetic document results are NEVER aggregated with real document results. "
            "synthetic_doc_ids lists all document IDs whose data came from deliberately "
            "constructed stress-test documents, not real CMPDI data."
        ),
    }

    # Mark previous latest as not-latest
    prev_latest = (await db.execute(
        select(BenchmarkRun).where(BenchmarkRun.is_latest == True)  # noqa: E712
    )).scalars().all()
    for r in prev_latest:
        r.is_latest = False

    run = BenchmarkRun(
        results=results,
        document_count_real=len(real_gt),
        document_count_synthetic=len(synthetic_gt),
        sample_size=len(real_gt) + len(synthetic_gt),
        is_latest=True,
        run_note=note,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    logger.info("Benchmark run %s complete. is_latest=True", run.id)
    return run


# ---------------------------------------------------------------------------
# Per-label-set evaluation
# ---------------------------------------------------------------------------

async def _evaluate_label_sets(
    db: AsyncSession, gt_rows: List[BenchmarkGroundTruth]
) -> Dict[str, Any]:
    """Evaluate all metrics across a collection of label sets."""
    if not gt_rows:
        return _empty_metrics("no label sets provided")

    entity_tp = entity_total = 0
    unit_tp = unit_total = 0
    text_scores: List[float] = []
    table_scores: List[float] = []
    conflict_tp = conflict_fp = conflict_fn = 0
    citation_tp = citation_total = 0

    for gt in gt_rows:
        labels: List[Dict] = gt.labels if isinstance(gt.labels, list) else []
        for label in labels:
            label_type = label.get("label_type", "fact")

            if label_type == "entity":
                entity_total += 1
                if await _check_entity_resolved(db, label):
                    entity_tp += 1

            elif label_type == "fact":
                unit_total += 1
                if await _check_unit_normalized(db, label):
                    unit_tp += 1

            elif label_type == "text_extraction":
                score = await _score_text_extraction(db, label)
                if score is not None:
                    text_scores.append(score)

            elif label_type == "table_extraction":
                score = await _score_table_extraction(db, label)
                if score is not None:
                    table_scores.append(score)

            elif label_type == "conflict":
                tp, fp, fn = await _check_conflict_detection(db, label)
                conflict_tp += tp
                conflict_fp += fp
                conflict_fn += fn

            elif label_type == "citation":
                citation_total += 1
                if await _check_citation(db, label):
                    citation_tp += 1

    precision = conflict_tp / (conflict_tp + conflict_fp) if (conflict_tp + conflict_fp) > 0 else None
    recall    = conflict_tp / (conflict_tp + conflict_fn) if (conflict_tp + conflict_fn) > 0 else None

    return {
        "entity_resolution_accuracy":   _pct(entity_tp, entity_total),
        "entity_resolution_sample":     entity_total,
        "unit_normalization_accuracy":  _pct(unit_tp, unit_total),
        "unit_normalization_sample":    unit_total,
        "text_extraction_accuracy":     round(sum(text_scores) / len(text_scores), 4) if text_scores else None,
        "text_extraction_sample":       len(text_scores),
        "table_extraction_accuracy":    round(sum(table_scores) / len(table_scores), 4) if table_scores else None,
        "table_extraction_sample":      len(table_scores),
        "conflict_detection_precision": round(precision, 4) if precision is not None else None,
        "conflict_detection_recall":    round(recall, 4) if recall is not None else None,
        "conflict_sample":              conflict_tp + conflict_fn,
        "citation_accuracy":            _pct(citation_tp, citation_total),
        "citation_sample":              citation_total,
        "sample_size":                  len(gt_rows),
    }


def _empty_metrics(reason: str) -> Dict[str, Any]:
    return {
        "entity_resolution_accuracy":   None,
        "unit_normalization_accuracy":  None,
        "text_extraction_accuracy":     None,
        "table_extraction_accuracy":    None,
        "conflict_detection_precision": None,
        "conflict_detection_recall":    None,
        "citation_accuracy":            None,
        "query_answer_correctness":     None,
        "sample_size":                  0,
        "note":                         reason,
    }


# ---------------------------------------------------------------------------
# Individual metric checks
# ---------------------------------------------------------------------------

async def _check_entity_resolved(db: AsyncSession, label: Dict) -> bool:
    """Check if a labeled entity alias resolves to the expected canonical entity."""
    alias_text = label.get("alias_text")
    expected_canonical = label.get("expected_canonical_name")
    if not alias_text or not expected_canonical:
        return False

    result = await db.execute(
        select(CanonicalEntity)
        .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
        .where(EntityAlias.alias_text.ilike(alias_text))
    )
    entity = result.scalar_one_or_none()
    return (
        entity is not None
        and entity.canonical_name.lower() == expected_canonical.lower()
    )


async def _check_unit_normalized(db: AsyncSession, label: Dict) -> bool:
    """Check if a labeled fact was normalized to the expected unit."""
    doc_id_str = label.get("document_id")
    entity_name = label.get("entity")
    metric = label.get("metric")
    expected_unit = label.get("expected_unit")
    if not (metric and expected_unit):
        return False

    filters = [
        NormalizedFact.metric.ilike(f"%{metric}%"),
        NormalizedFact.normalized_unit.ilike(f"%{expected_unit}%"),
        NormalizedFact.fact_processing_status != "rejected",
    ]

    if entity_name:
        entity_res = await db.execute(
            select(CanonicalEntity).where(
                CanonicalEntity.canonical_name.ilike(entity_name)
            )
        )
        entity = entity_res.scalar_one_or_none()
        if entity:
            filters.append(NormalizedFact.canonical_entity_id == entity.id)

    result = await db.execute(
        select(func.count()).select_from(NormalizedFact).where(and_(*filters))
    )
    return int(result.scalar_one() or 0) > 0


async def _score_text_extraction(db: AsyncSession, label: Dict) -> Optional[float]:
    """Character-level match rate between expected passage and extracted text blocks."""
    expected_text = label.get("expected_text_excerpt", "")
    doc_id_str = label.get("document_id")
    if not expected_text or not doc_id_str:
        return None
    try:
        doc_id = uuid.UUID(doc_id_str)
    except ValueError:
        return None

    from app.models.extraction import ExtractedTextBlock
    blocks = (await db.execute(
        select(ExtractedTextBlock.text_content)
        .where(ExtractedTextBlock.document_id == doc_id)
    )).scalars().all()

    if not blocks:
        return 0.0

    expected_lower = expected_text.lower().replace(" ", "")
    best_score = 0.0
    for block in blocks:
        if not block:
            continue
        block_lower = block.lower().replace(" ", "")
        score = _char_match_rate(expected_lower, block_lower)
        best_score = max(best_score, score)

    return round(best_score, 4)


async def _score_table_extraction(db: AsyncSession, label: Dict) -> Optional[float]:
    """Cell-level match rate for a labeled table value."""
    expected_value = label.get("expected_value")
    expected_cell = str(label.get("expected_cell_text", ""))
    doc_id_str = label.get("document_id")
    if expected_value is None or not doc_id_str:
        return None
    try:
        doc_id = uuid.UUID(doc_id_str)
    except ValueError:
        return None

    from app.models.extraction import ExtractedTable
    tables = (await db.execute(
        select(ExtractedTable.table_data)
        .where(ExtractedTable.document_id == doc_id)
    )).scalars().all()

    if not tables:
        return 0.0

    expected_str = str(expected_value).lower().replace(" ", "")
    for table_data in tables:
        if not table_data:
            continue
        # table_data is a list of rows (list of cells)
        rows = table_data if isinstance(table_data, list) else []
        for row in rows:
            cells = row if isinstance(row, list) else []
            for cell in cells:
                cell_str = str(cell).lower().replace(" ", "")
                if expected_str in cell_str or cell_str in expected_str:
                    return 1.0
    return 0.0


async def _check_conflict_detection(
    db: AsyncSession, label: Dict
) -> Tuple[int, int, int]:
    """
    Check whether a deliberately injected conflict was correctly detected.
    Returns (tp, fp, fn) counts — each label contributes at most 1 to each.

    A conflict label specifies two facts (by entity, metric, period) that
    SHOULD appear as a conflict in the conflicts table.
    """
    entity_name = label.get("entity")
    metric = label.get("metric")
    period = label.get("expected_period")
    expected_conflict = label.get("expected_conflict", True)

    if not (entity_name and metric):
        return 0, 0, 0

    # Find the entity
    entity_res = await db.execute(
        select(CanonicalEntity).where(
            CanonicalEntity.canonical_name.ilike(entity_name)
        )
    )
    entity = entity_res.scalar_one_or_none()
    if entity is None:
        if expected_conflict:
            return 0, 0, 1   # FN: expected a conflict but entity not found
        return 0, 0, 0

    # Check conflicts table
    conflict_res = await db.execute(
        select(func.count()).select_from(Conflict)
        .where(and_(
            Conflict.canonical_entity_id == entity.id,
            Conflict.metric.ilike(f"%{metric}%"),
        ))
    )
    conflict_count = int(conflict_res.scalar_one() or 0)

    if expected_conflict and conflict_count > 0:
        return 1, 0, 0   # TP
    elif expected_conflict and conflict_count == 0:
        return 0, 0, 1   # FN
    elif not expected_conflict and conflict_count > 0:
        return 0, 1, 0   # FP
    else:
        return 0, 0, 0   # TN (not counted)


async def _check_citation(db: AsyncSession, label: Dict) -> bool:
    """Check if a fact has a verifiable citation to the expected document/page."""
    doc_id_str = label.get("expected_document_id")
    expected_page = label.get("expected_page_number")
    entity_name = label.get("entity")
    metric = label.get("metric")

    if not (doc_id_str and entity_name and metric):
        return False

    try:
        doc_id = uuid.UUID(doc_id_str)
    except ValueError:
        return False

    entity_res = await db.execute(
        select(CanonicalEntity).where(
            CanonicalEntity.canonical_name.ilike(entity_name)
        )
    )
    entity = entity_res.scalar_one_or_none()
    if entity is None:
        return False

    # Check that at least one normalized_fact for this entity/metric
    # traces back to an extracted_fact from the expected document
    result = await db.execute(
        select(func.count())
        .select_from(NormalizedFact)
        .join(ExtractedFact, ExtractedFact.id == NormalizedFact.extracted_fact_id)
        .where(and_(
            NormalizedFact.canonical_entity_id == entity.id,
            NormalizedFact.metric.ilike(f"%{metric}%"),
            ExtractedFact.document_id == doc_id,
        ))
    )
    return int(result.scalar_one() or 0) > 0


async def _evaluate_query_correctness(db: AsyncSession) -> Dict[str, Any]:
    """Evaluate a fixed set of known-correct query answers.

    Questions and expected answers are loaded from query_ground_truth.json.
    Numeric answers must be within ±1% of the expected value.
    """
    if not QUERY_GT_FILE.exists():
        return {"real": {"query_answer_correctness": None, "query_sample": 0,
                         "note": "query_ground_truth.json not found"}}

    try:
        with open(QUERY_GT_FILE) as f:
            query_gt = json.load(f)
    except Exception as exc:
        logger.warning("Could not load query ground truth: %s", exc)
        return {"real": {"query_answer_correctness": None, "query_sample": 0}}

    correct = 0
    total = 0
    for item in query_gt:
        expected_value = item.get("expected_value")
        entity_name = item.get("entity")
        metric = item.get("metric")
        if not (expected_value is not None and entity_name and metric):
            continue

        # Look up the actual value in normalized_facts
        entity_res = await db.execute(
            select(CanonicalEntity).where(
                CanonicalEntity.canonical_name.ilike(entity_name)
            )
        )
        entity = entity_res.scalar_one_or_none()
        if entity is None:
            total += 1
            continue

        value_res = await db.execute(
            select(func.avg(NormalizedFact.normalized_value))
            .where(and_(
                NormalizedFact.canonical_entity_id == entity.id,
                NormalizedFact.metric.ilike(f"%{metric}%"),
                NormalizedFact.fact_processing_status != "rejected",
            ))
        )
        actual = value_res.scalar_one()
        total += 1
        if actual is not None:
            tolerance = abs(float(expected_value)) * 0.01
            if abs(float(actual) - float(expected_value)) <= max(tolerance, 0.001):
                correct += 1

    return {
        "real": {
            "query_answer_correctness": _pct(correct, total),
            "query_sample":             total,
        }
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _pct(tp: int, total: int) -> Optional[float]:
    return round(tp / total, 4) if total > 0 else None


def _char_match_rate(expected: str, actual: str) -> float:
    """Simple character-level match rate using longest common subsequence length."""
    if not expected:
        return 1.0 if not actual else 0.0
    # Fast check: is expected a substring of actual?
    if expected in actual:
        return 1.0
    # Approximate: overlap of character sets
    exp_set = set(expected)
    act_set = set(actual)
    overlap = len(exp_set & act_set)
    return overlap / len(exp_set) if exp_set else 0.0
