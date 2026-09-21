"""Report Content Assembler — Phase 4.

Builds the shared ReportContent dataclass from Phase 3 Analytics Service
output and Phase 2 validation/conflict data.

NO LLM calls happen here. This module is deterministic — all numbers come
from the Analytics Service and the DB. The narrative_generator.py module
calls the LLM on top of the assembled content.

Every figure in the assembled content carries a citation_key that maps to a
Citation object linking back to the source normalized_fact.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.extraction import ExtractedTextBlock, ExtractedTable
from app.models.page import Page
from app.models.phase2 import (
    CanonicalEntity, Conflict, ExtractedFact, NormalizedFact, ValidationFlag,
)
from app.services.analytics.analytics_service import get_trend as analytics_get_trend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report content dataclasses (shared by all exporters)
# ---------------------------------------------------------------------------

@dataclass
class Citation:
    claim_key:             str
    normalized_fact_id:    uuid.UUID
    document_id:           uuid.UUID
    document_filename:     str
    page_number:           Optional[int]
    excerpt:               str
    extraction_confidence: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_key":             self.claim_key,
            "normalized_fact_id":    str(self.normalized_fact_id),
            "document_id":           str(self.document_id),
            "document_filename":     self.document_filename,
            "page_number":           self.page_number,
            "excerpt":               self.excerpt,
            "extraction_confidence": self.extraction_confidence,
        }


@dataclass
class NarrativeSection:
    heading:       str
    text:          str = ""          # filled by narrative_generator.py
    citation_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"heading": self.heading, "text": self.text, "citation_keys": self.citation_keys}


@dataclass
class TableSection:
    heading: str
    rows:    List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"heading": self.heading, "rows": self.rows}


@dataclass
class DataPoint:
    period_label: str
    period_start: Optional[date]
    period_end:   Optional[date]
    value:        Optional[float]
    fact_id:      Optional[uuid.UUID]
    has_conflict: bool = False
    citation_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label": self.period_label,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end":   self.period_end.isoformat()   if self.period_end   else None,
            "value":        self.value,
            "fact_id":      str(self.fact_id) if self.fact_id else None,
            "has_conflict": self.has_conflict,
            "citation_key": self.citation_key,
        }


@dataclass
class SeriesData:
    entity_name: str
    metric:      str
    unit:        Optional[str]
    data_points: List[DataPoint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "metric":      self.metric,
            "unit":        self.unit,
            "data_points": [dp.to_dict() for dp in self.data_points],
        }


@dataclass
class TrendSection:
    heading: str
    series:  List[SeriesData] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"heading": self.heading, "series": [s.to_dict() for s in self.series]}


@dataclass
class WarningsSection:
    heading:        str
    open_flags:     List[Dict[str, Any]] = field(default_factory=list)
    open_conflicts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading":        self.heading,
            "open_flags":     self.open_flags,
            "open_conflicts": self.open_conflicts,
        }


@dataclass
class ReportScope:
    entity_ids:   Optional[List[uuid.UUID]]
    metrics:      Optional[List[str]]
    period_start: date
    period_end:   date
    label:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_ids":   [str(e) for e in self.entity_ids] if self.entity_ids else None,
            "metrics":      self.metrics,
            "period_start": self.period_start.isoformat(),
            "period_end":   self.period_end.isoformat(),
            "label":        self.label,
        }


@dataclass
class ReportContent:
    """Single shared internal report model — all exporters render from this."""
    report_id:             uuid.UUID
    generated_at:          datetime
    scope:                 ReportScope
    executive_summary:     NarrativeSection
    production_overview:   TableSection
    historical_trends:     TrendSection
    comparative_analysis:  TableSection
    data_quality_warnings: WarningsSection
    recommendations:       Optional[NarrativeSection]
    citations:             List[Citation] = field(default_factory=list)
    dq_warning_count:      int = 0
    generation_time_seconds: float = 0.0
    model_used:            str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":             str(self.report_id),
            "generated_at":          self.generated_at.isoformat(),
            "scope":                 self.scope.to_dict(),
            "executive_summary":     self.executive_summary.to_dict(),
            "production_overview":   self.production_overview.to_dict(),
            "historical_trends":     self.historical_trends.to_dict(),
            "comparative_analysis":  self.comparative_analysis.to_dict(),
            "data_quality_warnings": self.data_quality_warnings.to_dict(),
            "recommendations":       self.recommendations.to_dict() if self.recommendations else None,
            "citations":             [c.to_dict() for c in self.citations],
            "dq_warning_count":      self.dq_warning_count,
            "generation_time_seconds": self.generation_time_seconds,
            "model_used":            self.model_used,
        }


# ---------------------------------------------------------------------------
# Citation registry (builds claim_key → Citation mapping during assembly)
# ---------------------------------------------------------------------------

class _CitationRegistry:
    def __init__(self) -> None:
        self._map: Dict[uuid.UUID, Citation] = {}
        self._counter = 0

    def register(self, citation: Citation) -> None:
        self._map[citation.normalized_fact_id] = citation

    def get_or_create_key(self, fact_id: Optional[uuid.UUID]) -> Optional[str]:
        if fact_id is None:
            return None
        if fact_id in self._map:
            return self._map[fact_id].claim_key
        return None

    @property
    def citations(self) -> List[Citation]:
        return list(self._map.values())

    def next_key(self) -> str:
        self._counter += 1
        return f"C{self._counter:03d}"


# ---------------------------------------------------------------------------
# Main assembler function
# ---------------------------------------------------------------------------

async def assemble_report(
    *,
    db: AsyncSession,
    report_id: uuid.UUID,
    scope: ReportScope,
) -> ReportContent:
    """Build the structured ReportContent from analytics + DB data.

    No LLM calls. Returns a ReportContent with empty narrative .text fields —
    those are filled by narrative_generator.py afterwards.
    """
    registry = _CitationRegistry()

    # Resolve entity names
    entity_names = await _resolve_entity_names(db, scope.entity_ids)
    metrics = scope.metrics or await _all_metrics_for_scope(db, scope)

    # 1. Fetch time-series trends for each entity+metric in scope
    trend_section, trend_citations = await _build_trend_section(
        db, scope, entity_names, metrics, registry
    )

    # 2. Production overview — latest-period values per entity+metric
    overview_section = _build_overview_from_trends(trend_section)

    # 3. Comparative analysis — entity-vs-entity for each metric
    comparison_section = _build_comparison_section(trend_section)

    # 4. Data quality warnings — open flags + open conflicts in scope
    warnings_section = await _build_warnings_section(db, scope, entity_names)
    dq_count = len(warnings_section.open_flags) + len(warnings_section.open_conflicts)

    # 5. Stub narrative sections (text filled by narrative_generator later)
    executive_summary = NarrativeSection(
        heading="Executive Summary",
        citation_keys=[c.claim_key for c in registry.citations[:10]],
    )
    recommendations: Optional[NarrativeSection] = None
    # Recommendations only if there are anomalies or significant YoY changes
    has_significant_findings = any(
        dp.has_conflict or (dp.value is not None)
        for s in trend_section.series
        for dp in s.data_points
    )
    if has_significant_findings:
        recommendations = NarrativeSection(
            heading="Recommendations",
            citation_keys=[c.claim_key for c in registry.citations[:5]],
        )

    return ReportContent(
        report_id=report_id,
        generated_at=datetime.now(timezone.utc),
        scope=scope,
        executive_summary=executive_summary,
        production_overview=overview_section,
        historical_trends=trend_section,
        comparative_analysis=comparison_section,
        data_quality_warnings=warnings_section,
        recommendations=recommendations,
        citations=registry.citations,
        dq_warning_count=dq_count,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _resolve_entity_names(
    db: AsyncSession,
    entity_ids: Optional[List[uuid.UUID]],
) -> Dict[uuid.UUID, str]:
    if not entity_ids:
        res = await db.execute(select(CanonicalEntity))
        entities = res.scalars().all()
    else:
        res = await db.execute(
            select(CanonicalEntity).where(CanonicalEntity.id.in_(entity_ids))
        )
        entities = res.scalars().all()
    return {e.id: e.canonical_name for e in entities}


async def _all_metrics_for_scope(
    db: AsyncSession,
    scope: ReportScope,
) -> List[str]:
    """Return distinct metric names present in the time period."""
    from sqlalchemy import func as sqlfunc, distinct
    q = (
        select(NormalizedFact.metric)
        .where(
            and_(
                NormalizedFact.metric.isnot(None),
                NormalizedFact.period_start >= scope.period_start,
                NormalizedFact.period_end   <= scope.period_end,
                NormalizedFact.fact_processing_status != "rejected",
            )
        )
        .distinct()
        .limit(20)
    )
    res = await db.execute(q)
    metrics = [row[0] for row in res.all() if row[0]]
    return metrics


async def _build_trend_section(
    db: AsyncSession,
    scope: ReportScope,
    entity_names: Dict[uuid.UUID, str],
    metrics: List[str],
    registry: _CitationRegistry,
) -> Tuple[TrendSection, List[Citation]]:
    """Fetch time-series for every (entity, metric) combination in scope.

    Calls the analytics service's module-level get_trend() function directly.
    Converts scope.period_start/period_end (date objects) to year integers as
    required by the analytics service API.
    """
    section = TrendSection(heading="Historical Trends")
    citations: List[Citation] = []

    entity_ids = scope.entity_ids or list(entity_names.keys())
    start_year = scope.period_start.year
    end_year   = scope.period_end.year

    for metric in metrics:
        for eid in entity_ids:
            ename = entity_names.get(eid, str(eid))
            try:
                result = await analytics_get_trend(
                    db,
                    entity_id=eid,
                    metric=metric,
                    start_year=start_year,
                    end_year=end_year,
                )
            except Exception as exc:
                logger.warning("Trend query failed for %s/%s: %s", ename, metric, exc)
                continue

            if not result or not result.series:
                continue

            series = SeriesData(
                entity_name=ename,
                metric=metric,
                unit=result.unit,
            )
            for dp in result.series:
                cit = await _citation_for_fact(db, dp.fact_id, registry)
                dp_out = DataPoint(
                    period_label=dp.period_label,
                    period_start=dp.period_start,
                    period_end=dp.period_end,
                    value=dp.value,
                    fact_id=dp.fact_id,
                    has_conflict=dp.has_conflict,
                    citation_key=cit.claim_key if cit else None,
                )
                series.data_points.append(dp_out)

            section.series.append(series)

    return section, citations


def _build_overview_from_trends(trend_section: TrendSection) -> TableSection:
    """Build a production overview table using the latest data point per series."""
    section = TableSection(heading="Production / Operational Overview")
    for s in trend_section.series:
        if not s.data_points:
            continue
        # Latest non-None data point
        latest = next(
            (dp for dp in reversed(s.data_points) if dp.value is not None), None
        )
        if latest is None:
            continue
        section.rows.append({
            "entity":       s.entity_name,
            "metric":       s.metric,
            "period":       latest.period_label,
            "value":        latest.value,
            "unit":         s.unit,
            "citation_key": latest.citation_key,
        })
    return section


def _build_comparison_section(trend_section: TrendSection) -> TableSection:
    """Entity-vs-entity comparison for each metric."""
    section = TableSection(heading="Comparative Analysis")
    # Group series by metric
    by_metric: Dict[str, List[SeriesData]] = {}
    for s in trend_section.series:
        by_metric.setdefault(s.metric, []).append(s)

    for metric, series_list in by_metric.items():
        if len(series_list) < 2:
            continue
        # Latest value per entity for this metric
        for s in series_list:
            latest = next(
                (dp for dp in reversed(s.data_points) if dp.value is not None), None
            )
            if latest is None:
                continue
            section.rows.append({
                "entity":       s.entity_name,
                "metric":       metric,
                "period":       latest.period_label,
                "value":        latest.value,
                "unit":         s.unit,
                "citation_key": latest.citation_key,
            })

    return section


async def _build_warnings_section(
    db: AsyncSession,
    scope: ReportScope,
    entity_names: Dict[uuid.UUID, str],
) -> WarningsSection:
    """Collect open flags and conflicts relevant to this report scope."""
    section = WarningsSection(heading="Data Quality Warnings")

    # Open flags for facts in the period
    flags_q = (
        select(ValidationFlag, NormalizedFact, CanonicalEntity)
        .join(NormalizedFact, NormalizedFact.id == ValidationFlag.normalized_fact_id)
        .outerjoin(CanonicalEntity, CanonicalEntity.id == NormalizedFact.canonical_entity_id)
        .where(
            and_(
                ValidationFlag.status == "open",
                NormalizedFact.period_start >= scope.period_start,
                NormalizedFact.period_end   <= scope.period_end,
            )
        )
        .limit(50)
    )
    if scope.entity_ids:
        flags_q = flags_q.where(
            NormalizedFact.canonical_entity_id.in_(scope.entity_ids)
        )
    if scope.metrics:
        flags_q = flags_q.where(NormalizedFact.metric.in_(scope.metrics))

    flags_res = await db.execute(flags_q)
    for flag, nf, entity in flags_res.all():
        section.open_flags.append({
            "flag_type":          flag.flag_type,
            "severity":           flag.severity,
            "detail":             flag.detail,
            "normalized_fact_id": str(nf.id),
            "entity_name":        entity.canonical_name if entity else None,
            "metric":             nf.metric,
        })

    # Open conflicts in scope
    conflicts_q = (
        select(Conflict, CanonicalEntity)
        .outerjoin(CanonicalEntity, CanonicalEntity.id == Conflict.canonical_entity_id)
        .where(
            and_(
                Conflict.status == "open",
                Conflict.period_start >= scope.period_start,
                Conflict.period_end   <= scope.period_end,
            )
        )
        .limit(20)
    )
    if scope.entity_ids:
        conflicts_q = conflicts_q.where(
            Conflict.canonical_entity_id.in_(scope.entity_ids)
        )
    if scope.metrics:
        conflicts_q = conflicts_q.where(Conflict.metric.in_(scope.metrics))

    conflicts_res = await db.execute(conflicts_q)
    for conflict, entity in conflicts_res.all():
        period = None
        if conflict.period_start and conflict.period_end:
            period = f"{conflict.period_start} → {conflict.period_end}"
        section.open_conflicts.append({
            "conflict_id": str(conflict.id),
            "entity_name": entity.canonical_name if entity else None,
            "metric":      conflict.metric,
            "period":      period,
            "delta_pct":   conflict.delta_pct,
            "fact_a_id":   str(conflict.fact_a_id),
            "fact_b_id":   str(conflict.fact_b_id),
        })

    return section


async def _citation_for_fact(
    db: AsyncSession,
    fact_id: Optional[uuid.UUID],
    registry: _CitationRegistry,
) -> Optional[Citation]:
    """Load or create a Citation for the given normalized_fact_id."""
    if fact_id is None:
        return None

    # Return existing citation if already registered
    existing = registry.get_or_create_key(fact_id)
    if existing:
        return registry._map.get(fact_id)

    try:
        nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == fact_id))
        nf = nf_res.scalar_one_or_none()
        if not nf:
            return None

        ef_res = await db.execute(select(ExtractedFact).where(ExtractedFact.id == nf.extracted_fact_id))
        ef = ef_res.scalar_one_or_none()
        if not ef:
            return None

        doc_res = await db.execute(select(Document).where(Document.id == ef.document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            return None

        pg_res = await db.execute(select(Page).where(Page.id == ef.page_id))
        pg = pg_res.scalar_one_or_none()

        excerpt = f"{ef.raw_entity_text or ''} {ef.raw_metric_text or ''}: {ef.raw_value}".strip()
        if ef.block_id:
            blk_res = await db.execute(select(ExtractedTextBlock).where(ExtractedTextBlock.id == ef.block_id))
            blk = blk_res.scalar_one_or_none()
            if blk:
                excerpt = (blk.text or "")[:300]

        cit = Citation(
            claim_key=registry.next_key(),
            normalized_fact_id=fact_id,
            document_id=doc.id,
            document_filename=doc.original_filename or doc.filename,
            page_number=pg.page_number if pg else None,
            excerpt=excerpt,
            extraction_confidence=ef.extraction_confidence,
        )
        registry.register(cit)
        return cit

    except Exception as exc:
        logger.warning("Could not build citation for fact %s: %s", fact_id, exc)
        return None
