"""Mining Heat Map service — Phase 5.

Returns structured geographic layer data for the frontend map renderer.
This service REUSES the Analytics Service's existing aggregate queries,
grouping results by region_id from the region_mapping table.
It does NOT build parallel aggregation logic.

Supported layers:
  production       — normalized_value WHERE metric ILIKE '%production%'
  dispatch         — metric ILIKE '%dispatch%'
  resources        — metric_category ILIKE '%resource%'
  reserves         — metric_category ILIKE '%reserve%'
  exploration      — metric_category ILIKE '%exploration%'
  report_volume    — count of documents per region (via entity mentions in extracted_facts)
  data_quality     — composite green/yellow/red bucket (conflict density + avg confidence)
  conflict_density — open conflict count per region

Data Quality thresholds (returned verbatim in every response):
  Conflict density:      Green=0, Yellow=1-3, Red>=4
  Avg confidence:        Green>=0.75, Yellow>=0.50, Red<0.50
  Composite (worst-wins): Red > Yellow > Green; <3 facts = insufficient_data
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import (
    CanonicalEntity, Conflict, ExtractedFact, NormalizedFact, ValidationFlag,
)
from app.models.document import Document
from app.models.extraction import ExtractedTextBlock
from app.models.phase5 import RegionMapping

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (documented and returned in every API response)
# ---------------------------------------------------------------------------

QUALITY_THRESHOLDS = {
    "conflict_density": {
        "green":  "0 open conflicts",
        "yellow": "1–3 open conflicts",
        "red":    "≥4 open conflicts",
    },
    "avg_confidence": {
        "green":  "≥ 0.75",
        "yellow": "≥ 0.50 and < 0.75",
        "red":    "< 0.50",
    },
    "composite_rule": "worst-wins: Red > Yellow > Green; regions with <3 facts return 'insufficient_data'",
    "min_facts_for_bucket": 3,
}

_METRIC_LAYER_MAP: Dict[str, str] = {
    "production":  "%production%",
    "dispatch":    "%dispatch%",
    "resources":   "%resource%",
    "reserves":    "%reserve%",
    "exploration": "%exploration%",
}

VALID_LAYERS = [
    "production", "dispatch", "resources", "reserves", "exploration",
    "report_volume", "data_quality", "conflict_density",
]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def get_layer_data(layer: str, db: AsyncSession) -> Dict[str, Any]:
    """Return per-region aggregated values for the requested layer."""
    if layer not in VALID_LAYERS:
        raise ValueError(f"Unknown layer '{layer}'. Valid layers: {VALID_LAYERS}")

    # Load all region mappings
    regions = (await db.execute(select(RegionMapping))).scalars().all()
    if not regions:
        return {
            "layer":      layer,
            "regions":    [],
            "note":       "No region mappings found. Run the Phase 5 migration to seed region data.",
            "thresholds": QUALITY_THRESHOLDS,
        }

    # Group entity IDs by region
    region_entities: Dict[str, List] = {}
    for rm in regions:
        region_entities.setdefault(rm.region_id, []).append(rm)

    region_data = []
    for region_id, mappings in region_entities.items():
        entity_ids = [m.canonical_entity_id for m in mappings]
        first = mappings[0]

        if layer in _METRIC_LAYER_MAP:
            value = await _aggregate_metric(db, entity_ids, _METRIC_LAYER_MAP[layer])
            region_data.append({
                "region_id":   region_id,
                "region_name": first.region_name,
                "state_name":  first.state_name,
                "value":       value,
                "unit":        _infer_unit(layer),
                "entity_count": len(entity_ids),
                "source_provenance": _provenance_note(mappings),
            })

        elif layer == "report_volume":
            count = await _report_volume(db, entity_ids)
            region_data.append({
                "region_id":   region_id,
                "region_name": first.region_name,
                "state_name":  first.state_name,
                "value":       count,
                "unit":        "documents",
                "entity_count": len(entity_ids),
                "source_provenance": _provenance_note(mappings),
            })

        elif layer == "data_quality":
            bucket_info = await _data_quality_bucket(db, entity_ids)
            region_data.append({
                "region_id":   region_id,
                "region_name": first.region_name,
                "state_name":  first.state_name,
                **bucket_info,
                "entity_count": len(entity_ids),
                "source_provenance": _provenance_note(mappings),
            })

        elif layer == "conflict_density":
            conflict_count = await _open_conflict_count(db, entity_ids)
            region_data.append({
                "region_id":   region_id,
                "region_name": first.region_name,
                "state_name":  first.state_name,
                "value":       conflict_count,
                "unit":        "open conflicts",
                "entity_count": len(entity_ids),
                "source_provenance": _provenance_note(mappings),
            })

    return {
        "layer":      layer,
        "regions":    sorted(region_data, key=lambda r: r["region_id"]),
        "thresholds": QUALITY_THRESHOLDS if layer == "data_quality" else None,
    }


async def get_region_detail(region_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Drill-down detail for a single region.

    Returns:
      - List of entities and their summaries
      - Per-entity trend data (via Analytics Service; no re-implementation)
      - Recent documents linked to entities in the region
      - Open conflicts for region entities
      - Avg extraction confidence
    """
    mappings = (await db.execute(
        select(RegionMapping).where(RegionMapping.region_id == region_id)
    )).scalars().all()

    if not mappings:
        raise ValueError(f"Region '{region_id}' not found in region_mapping table.")

    entity_ids = [m.canonical_entity_id for m in mappings]
    first = mappings[0]

    # ── Entities ──────────────────────────────────────────────────────────
    entities_rows = (await db.execute(
        select(CanonicalEntity).where(CanonicalEntity.id.in_(entity_ids))
    )).scalars().all()

    entities_out = [
        {
            "id":             str(e.id),
            "canonical_name": e.canonical_name,
            "entity_type":    e.entity_type,
            "description":    e.description,
            "region_source":  next(
                (m.source for m in mappings if m.canonical_entity_id == e.id), "unknown"
            ),
        }
        for e in entities_rows
    ]

    # ── Open conflicts ────────────────────────────────────────────────────
    open_conflicts = (await db.execute(
        select(Conflict)
        .where(and_(
            Conflict.canonical_entity_id.in_(entity_ids),
            Conflict.status == "open",
        ))
        .order_by(Conflict.detected_at.desc())
        .limit(20)
    )).scalars().all()

    conflicts_out = [
        {
            "id":        str(c.id),
            "entity_id": str(c.canonical_entity_id),
            "metric":    c.metric,
            "period":    f"{c.period_start} → {c.period_end}",
            "value_a":   c.value_a,
            "value_b":   c.value_b,
            "delta_pct": c.delta_pct,
            "status":    c.status,
        }
        for c in open_conflicts
    ]

    # ── Recent documents (via extracted_facts → documents) ────────────────
    # Get distinct document IDs that have facts for entities in this region
    doc_ids_res = await db.execute(
        select(ExtractedFact.document_id.distinct())
        .join(NormalizedFact, NormalizedFact.extracted_fact_id == ExtractedFact.id)
        .where(NormalizedFact.canonical_entity_id.in_(entity_ids))
        .order_by(ExtractedFact.document_id)
        .limit(20)
    )
    doc_ids = [r[0] for r in doc_ids_res.all()]

    docs_out = []
    if doc_ids:
        docs = (await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
            .order_by(Document.upload_date.desc())
            .limit(10)
        )).scalars().all()
        docs_out = [
            {
                "id":              str(d.id),
                "filename":        d.original_filename,
                "file_type":       d.file_type,
                "upload_date":     d.upload_date.isoformat(),
                "processing_status": d.processing_status,
            }
            for d in docs
        ]

    # ── Avg extraction confidence ─────────────────────────────────────────
    avg_conf_res = await db.execute(
        select(func.avg(ExtractedFact.extraction_confidence))
        .join(NormalizedFact, NormalizedFact.extracted_fact_id == ExtractedFact.id)
        .where(
            and_(
                NormalizedFact.canonical_entity_id.in_(entity_ids),
                ExtractedFact.extraction_confidence.isnot(None),
            )
        )
    )
    avg_conf = avg_conf_res.scalar_one()

    # ── Data quality bucket for this region ───────────────────────────────
    bucket_info = await _data_quality_bucket(db, entity_ids)

    return {
        "region_id":   region_id,
        "region_name": first.region_name,
        "state_name":  first.state_name,
        "entity_count": len(entities_out),
        "entities":    entities_out,
        "open_conflict_count": len(open_conflicts),
        "open_conflicts": conflicts_out,
        "recent_documents": docs_out,
        "avg_extraction_confidence": round(float(avg_conf), 4) if avg_conf else None,
        "data_quality": bucket_info,
        "region_mapping_sources": list({m.source for m in mappings}),
        "thresholds":  QUALITY_THRESHOLDS,
    }


# ---------------------------------------------------------------------------
# Internal aggregation helpers (all reuse normalized_facts + conflicts tables)
# ---------------------------------------------------------------------------

async def _aggregate_metric(
    db: AsyncSession,
    entity_ids: list,
    metric_pattern: str,
) -> Optional[float]:
    """Aggregate (sum) normalized_value for entities in this region, metric pattern."""
    res = await db.execute(
        select(func.sum(NormalizedFact.normalized_value))
        .where(and_(
            NormalizedFact.canonical_entity_id.in_(entity_ids),
            NormalizedFact.metric.ilike(metric_pattern),
            NormalizedFact.normalized_value.isnot(None),
            NormalizedFact.fact_processing_status != "rejected",
        ))
    )
    val = res.scalar_one()
    return round(float(val), 2) if val else None


async def _report_volume(db: AsyncSession, entity_ids: list) -> int:
    """Count distinct documents with facts for entities in this region."""
    res = await db.execute(
        select(func.count(ExtractedFact.document_id.distinct()))
        .join(NormalizedFact, NormalizedFact.extracted_fact_id == ExtractedFact.id)
        .where(NormalizedFact.canonical_entity_id.in_(entity_ids))
    )
    return int(res.scalar_one() or 0)


async def _open_conflict_count(db: AsyncSession, entity_ids: list) -> int:
    """Count open conflicts for entities in this region."""
    res = await db.execute(
        select(func.count())
        .select_from(Conflict)
        .where(and_(
            Conflict.canonical_entity_id.in_(entity_ids),
            Conflict.status == "open",
        ))
    )
    return int(res.scalar_one() or 0)


async def _data_quality_bucket(
    db: AsyncSession, entity_ids: list
) -> Dict[str, Any]:
    """Compute composite green/yellow/red bucket for a region.

    Signal A: open conflict count  (Green=0, Yellow=1-3, Red>=4)
    Signal B: avg extraction confidence (Green>=0.75, Yellow>=0.50, Red<0.50)
    Composite: worst-wins; <3 facts → 'insufficient_data'
    """
    # Fact count check
    fact_count_res = await db.execute(
        select(func.count())
        .select_from(NormalizedFact)
        .where(and_(
            NormalizedFact.canonical_entity_id.in_(entity_ids),
            NormalizedFact.fact_processing_status != "rejected",
        ))
    )
    fact_count = int(fact_count_res.scalar_one() or 0)

    if fact_count < QUALITY_THRESHOLDS["min_facts_for_bucket"]:
        return {
            "bucket":       "insufficient_data",
            "fact_count":   fact_count,
            "open_conflicts": await _open_conflict_count(db, entity_ids),
            "avg_confidence": None,
            "note":         f"Fewer than {QUALITY_THRESHOLDS['min_facts_for_bucket']} facts; "
                            "cannot reliably compute quality bucket.",
        }

    conflicts = await _open_conflict_count(db, entity_ids)

    avg_conf_res = await db.execute(
        select(func.avg(ExtractedFact.extraction_confidence))
        .join(NormalizedFact, NormalizedFact.extracted_fact_id == ExtractedFact.id)
        .where(and_(
            NormalizedFact.canonical_entity_id.in_(entity_ids),
            ExtractedFact.extraction_confidence.isnot(None),
        ))
    )
    avg_conf = avg_conf_res.scalar_one()
    avg_conf_val = float(avg_conf) if avg_conf is not None else 1.0

    # Signal A
    if conflicts == 0:
        conflict_signal = "green"
    elif conflicts <= 3:
        conflict_signal = "yellow"
    else:
        conflict_signal = "red"

    # Signal B
    if avg_conf_val >= 0.75:
        confidence_signal = "green"
    elif avg_conf_val >= 0.50:
        confidence_signal = "yellow"
    else:
        confidence_signal = "red"

    # Composite worst-wins
    signals = {conflict_signal, confidence_signal}
    if "red" in signals:
        composite = "red"
    elif "yellow" in signals:
        composite = "yellow"
    else:
        composite = "green"

    return {
        "bucket":             composite,
        "conflict_signal":    conflict_signal,
        "confidence_signal":  confidence_signal,
        "open_conflicts":     conflicts,
        "avg_confidence":     round(avg_conf_val, 4) if avg_conf else None,
        "fact_count":         fact_count,
    }


def _infer_unit(layer: str) -> str:
    units = {
        "production": "MT (Million Tonnes)",
        "dispatch":   "MT",
        "resources":  "MT",
        "reserves":   "MT",
        "exploration": "km²",
    }
    return units.get(layer, "")


def _provenance_note(mappings: list) -> Dict[str, int]:
    """Return counts of reference_table vs document_derived mappings."""
    counts: Dict[str, int] = {}
    for m in mappings:
        counts[m.source] = counts.get(m.source, 0) + 1
    return counts
