"""Deterministic Analytics Service — pure SQL/Python, zero LLM involvement.

All functions:
  - Return both the numeric result AND the list of normalized_fact IDs used.
  - Never call the LLM or perform any non-deterministic operation.
  - Check for open conflicts on every fact they touch and return them separately.

The Analytics Service is the single source of all numbers that appear in AI responses.
"""
from __future__ import annotations

import logging
import math
import statistics
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import CanonicalEntity, Conflict, ExtractedFact, NormalizedFact

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Return-type dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DataPoint:
    """A single time-series value from normalized_facts."""
    period_label:  str
    period_start:  Optional[object]   # date
    period_end:    Optional[object]   # date
    value:         Optional[float]
    fact_id:       Optional[uuid.UUID]
    has_conflict:  bool = False
    has_flag:      bool = False


@dataclass
class YoYChange:
    from_period:     str
    to_period:       str
    absolute_change: Optional[float]
    pct_change:      Optional[float]
    fact_ids_used:   List[uuid.UUID] = field(default_factory=list)


@dataclass
class AnomalyPoint:
    entity_id:    uuid.UUID
    period_label: str
    fact_id:      Optional[uuid.UUID]
    value:        Optional[float]
    mean:         float
    std_dev:      float
    z_score:      float
    note:         str


@dataclass
class EntityAnalytics:
    entity_id:     uuid.UUID
    entity_name:   str
    data_points:   List[DataPoint]   = field(default_factory=list)
    yoy_changes:   List[YoYChange]   = field(default_factory=list)
    cagr_pct:      Optional[float]   = None
    cagr_fact_ids: List[uuid.UUID]   = field(default_factory=list)


@dataclass
class TrendResult:
    entity_id:    uuid.UUID
    entity_name:  str
    metric:       str
    unit:         Optional[str]
    series:       List[DataPoint]  = field(default_factory=list)
    all_fact_ids: List[uuid.UUID]  = field(default_factory=list)


@dataclass
class ComparisonResult:
    metric:            str
    unit:              Optional[str]
    period_start_year: Optional[int]
    period_end_year:   Optional[int]
    entities:          List[EntityAnalytics] = field(default_factory=list)
    anomalies:         List[AnomalyPoint]    = field(default_factory=list)
    all_fact_ids:      List[uuid.UUID]       = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_trend(
    db: AsyncSession,
    entity_id: uuid.UUID,
    metric: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> TrendResult:
    """Fetch time-series values for one entity/metric.

    Returns DataPoints sorted by period_start ascending, each tagged with its fact_id
    and conflict/flag status.
    """
    entity = await _get_entity(db, entity_id)
    facts = await _fetch_facts(db, [entity_id], metric, start_year, end_year)
    conflict_ids = await _open_conflict_fact_ids(db, [f.id for f in facts])
    flag_ids = await _flagged_fact_ids(db, [f.id for f in facts])
    unit = facts[0].normalized_unit if facts else None

    series = [
        DataPoint(
            period_label=f.period_label or _label(f),
            period_start=f.period_start,
            period_end=f.period_end,
            value=f.normalized_value,
            fact_id=f.id,
            has_conflict=f.id in conflict_ids,
            has_flag=f.id in flag_ids,
        )
        for f in facts
    ]

    return TrendResult(
        entity_id=entity_id,
        entity_name=entity.canonical_name if entity else str(entity_id),
        metric=metric,
        unit=unit,
        series=series,
        all_fact_ids=[f.id for f in facts],
    )


async def get_comparison(
    db: AsyncSession,
    entity_ids: List[uuid.UUID],
    metric: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> ComparisonResult:
    """Compare a metric across multiple entities over a period range.

    For each entity: fetches facts, computes YoY changes and CAGR.
    Also detects anomalies (z-score based) across each entity's own history.
    """
    all_fact_ids: List[uuid.UUID] = []
    entities_out: List[EntityAnalytics] = []
    anomalies_out: List[AnomalyPoint] = []
    unit: Optional[str] = None

    # Collect all fact IDs to do a single conflict/flag lookup
    all_facts_by_entity: Dict[uuid.UUID, List[NormalizedFact]] = {}
    for eid in entity_ids:
        facts = await _fetch_facts(db, [eid], metric, start_year, end_year)
        all_facts_by_entity[eid] = facts
        all_fact_ids.extend(f.id for f in facts)
        if facts and unit is None:
            unit = facts[0].normalized_unit

    conflict_ids = await _open_conflict_fact_ids(db, all_fact_ids)
    flag_ids = await _flagged_fact_ids(db, all_fact_ids)

    for eid in entity_ids:
        facts = all_facts_by_entity[eid]
        entity = await _get_entity(db, eid)
        entity_name = entity.canonical_name if entity else str(eid)

        data_points = [
            DataPoint(
                period_label=f.period_label or _label(f),
                period_start=f.period_start,
                period_end=f.period_end,
                value=f.normalized_value,
                fact_id=f.id,
                has_conflict=f.id in conflict_ids,
                has_flag=f.id in flag_ids,
            )
            for f in facts
        ]

        yoy = compute_yoy(data_points)
        cagr, cagr_ids = compute_cagr(data_points, [f.id for f in facts])
        entity_anomalies = detect_anomalies_for_series(data_points, eid)

        entities_out.append(EntityAnalytics(
            entity_id=eid,
            entity_name=entity_name,
            data_points=data_points,
            yoy_changes=yoy,
            cagr_pct=cagr,
            cagr_fact_ids=cagr_ids,
        ))
        anomalies_out.extend(entity_anomalies)

    return ComparisonResult(
        metric=metric,
        unit=unit,
        period_start_year=start_year,
        period_end_year=end_year,
        entities=entities_out,
        anomalies=anomalies_out,
        all_fact_ids=all_fact_ids,
    )


def compute_yoy(data_points: List[DataPoint]) -> List[YoYChange]:
    """Year-over-year change between consecutive data points.

    Returns changes sorted chronologically. All arithmetic is done here — never by LLM.
    """
    # Filter out points with no value and sort chronologically
    valid = sorted(
        [dp for dp in data_points if dp.value is not None and dp.period_start is not None],
        key=lambda dp: dp.period_start,
    )

    changes: List[YoYChange] = []
    for i in range(1, len(valid)):
        prev, curr = valid[i - 1], valid[i]
        abs_change = curr.value - prev.value if (curr.value is not None and prev.value is not None) else None
        pct_change = (abs_change / prev.value * 100) if (abs_change is not None and prev.value != 0) else None
        fids = [fid for fid in [prev.fact_id, curr.fact_id] if fid is not None]
        changes.append(YoYChange(
            from_period=prev.period_label,
            to_period=curr.period_label,
            absolute_change=round(abs_change, 4) if abs_change is not None else None,
            pct_change=round(pct_change, 2) if pct_change is not None else None,
            fact_ids_used=fids,
        ))
    return changes


def compute_cagr(
    data_points: List[DataPoint],
    fact_ids: List[uuid.UUID],
) -> Tuple[Optional[float], List[uuid.UUID]]:
    """Compound Annual Growth Rate between earliest and latest data point.

    Formula: CAGR = (end_value / start_value)^(1/n_years) − 1
    Returns (cagr_pct, [start_fact_id, end_fact_id]).
    Returns (None, []) if fewer than 2 data points with valid values and dates.
    """
    valid = sorted(
        [dp for dp in data_points if dp.value is not None
         and dp.value > 0 and dp.period_start is not None],
        key=lambda dp: dp.period_start,
    )
    if len(valid) < 2:
        return None, []

    first, last = valid[0], valid[-1]
    # Compute years between period starts
    years = (last.period_start - first.period_start).days / 365.25
    if years <= 0 or first.value == 0:
        return None, []

    cagr = ((last.value / first.value) ** (1.0 / years) - 1.0) * 100
    ids = [fid for fid in [first.fact_id, last.fact_id] if fid is not None]
    return round(cagr, 2), ids


def detect_anomalies_for_series(
    data_points: List[DataPoint],
    entity_id: uuid.UUID,
    z_threshold: float = 2.0,
) -> List[AnomalyPoint]:
    """Z-score anomaly detection within a single entity's time series.

    A data point is anomalous if |z-score| >= z_threshold (default 2.0 σ).
    Requires at least 3 valid values to compute meaningful statistics.
    """
    valid = [dp for dp in data_points if dp.value is not None]
    if len(valid) < 3:
        return []

    values = [dp.value for dp in valid]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    if std_dev == 0:
        return []

    anomalies: List[AnomalyPoint] = []
    for dp in valid:
        z = (dp.value - mean) / std_dev
        if abs(z) >= z_threshold:
            anomalies.append(AnomalyPoint(
                entity_id=entity_id,
                period_label=dp.period_label,
                fact_id=dp.fact_id,
                value=dp.value,
                mean=round(mean, 4),
                std_dev=round(std_dev, 4),
                z_score=round(z, 2),
                note=f"Value is {abs(z):.1f}σ {'above' if z > 0 else 'below'} entity historical mean",
            ))
    return anomalies


async def get_facts_for_entity_metric_period(
    db: AsyncSession,
    entity_id: uuid.UUID,
    metric: str,
    period_year: int,
) -> List[NormalizedFact]:
    """Fetch facts for a specific entity/metric/year — used by Why-Change engine."""
    return await _fetch_facts(db, [entity_id], metric, period_year - 1, period_year + 1)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _fetch_facts(
    db: AsyncSession,
    entity_ids: List[uuid.UUID],
    metric: str,
    start_year: Optional[int],
    end_year: Optional[int],
) -> List[NormalizedFact]:
    """Fetch normalized facts matching the entity/metric/period criteria, sorted by period."""
    filters = [
        NormalizedFact.canonical_entity_id.in_(entity_ids),
        NormalizedFact.metric == metric,
        NormalizedFact.normalized_value.is_not(None),
        NormalizedFact.fact_processing_status != "failed",
    ]
    if start_year is not None:
        filters.append(
            func.extract("year", NormalizedFact.period_end) >= start_year
        )
    if end_year is not None:
        filters.append(
            func.extract("year", NormalizedFact.period_start) <= end_year
        )

    result = await db.execute(
        select(NormalizedFact)
        .where(and_(*filters))
        .order_by(NormalizedFact.period_start.asc().nullsfirst())
    )
    return list(result.scalars().all())


async def _get_entity(db: AsyncSession, entity_id: uuid.UUID) -> Optional[CanonicalEntity]:
    result = await db.execute(
        select(CanonicalEntity).where(CanonicalEntity.id == entity_id)
    )
    return result.scalar_one_or_none()


async def _open_conflict_fact_ids(
    db: AsyncSession,
    fact_ids: List[uuid.UUID],
) -> set[uuid.UUID]:
    """Return the set of fact_ids that are part of an OPEN conflict."""
    if not fact_ids:
        return set()
    result = await db.execute(
        select(Conflict.fact_a_id, Conflict.fact_b_id)
        .where(
            and_(
                Conflict.status == "open",
                (Conflict.fact_a_id.in_(fact_ids)) | (Conflict.fact_b_id.in_(fact_ids)),
            )
        )
    )
    conflicted: set[uuid.UUID] = set()
    for row in result.all():
        if row.fact_a_id in fact_ids:
            conflicted.add(row.fact_a_id)
        if row.fact_b_id in fact_ids:
            conflicted.add(row.fact_b_id)
    return conflicted


async def _flagged_fact_ids(
    db: AsyncSession,
    fact_ids: List[uuid.UUID],
) -> set[uuid.UUID]:
    """Return set of fact_ids that have at least one open validation flag."""
    if not fact_ids:
        return set()
    from app.models.phase2 import ValidationFlag
    result = await db.execute(
        select(ValidationFlag.normalized_fact_id)
        .where(
            and_(
                ValidationFlag.normalized_fact_id.in_(fact_ids),
                ValidationFlag.status == "open",
            )
        )
        .distinct()
    )
    return {row[0] for row in result.all()}


async def get_open_conflicts_for_facts(
    db: AsyncSession,
    fact_ids: List[uuid.UUID],
) -> List[Conflict]:
    """Return full Conflict records for all open conflicts involving these fact_ids."""
    if not fact_ids:
        return []
    result = await db.execute(
        select(Conflict).where(
            and_(
                Conflict.status == "open",
                (Conflict.fact_a_id.in_(fact_ids)) | (Conflict.fact_b_id.in_(fact_ids)),
            )
        )
    )
    return list(result.scalars().all())


def _label(fact: NormalizedFact) -> str:
    """Fallback period label from period_start date."""
    if fact.period_start:
        y = fact.period_start.year
        m = fact.period_start.month
        # Indian fiscal year: April start
        if m >= 4:
            return f"FY{y}/{str(y + 1)[-2:]}"
        else:
            return f"FY{y - 1}/{str(y)[-2:]}"
    return "unknown"
