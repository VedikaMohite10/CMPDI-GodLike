"""Analytics router — pure SQL/Python endpoints, no LLM involvement.

POST /analytics/compare  — comparative analysis across entities/metrics/periods
POST /analytics/trend    — time series for a single entity/metric (suitable for charting)
POST /analytics/why-did-this-change — Why-Change engine (LLM-assisted, fully packaged)
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2 import CanonicalEntity
from app.schemas.query import (
    AnalyticsCompareRequest,
    AnalyticsCompareResponse,
    AnalyticsTrendRequest,
    AnalyticsTrendResponse,
    AnalyticsDataPoint,
    AnomalyPoint,
    EntityAnalytics,
    WhyChangeRequest,
    WhyChangeResponse,
    WhyChangeDetail,
    CitedPassage,
)
from app.services.analytics import analytics_service
from app.services.analytics.analytics_service import get_open_conflicts_for_facts
from app.services.analytics.why_change_engine import run_why_change
from app.services.explainer import package_response
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# POST /analytics/compare
# ---------------------------------------------------------------------------

@router.post(
    "/compare",
    response_model=AnalyticsCompareResponse,
    summary="Comparative analysis across entities for a metric and period",
    description=(
        "Pure deterministic analytics — no LLM involved. "
        "Returns YoY changes, CAGR, and anomalies for each requested entity, "
        "with every data point tagged with its source fact_id and conflict/flag status."
    ),
)
async def compare(
    request: AnalyticsCompareRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await analytics_service.get_comparison(
            db=db,
            entity_ids=request.entity_ids,
            metric=request.metric,
            start_year=request.period_start_year,
            end_year=request.period_end_year,
        )
    except Exception as exc:
        logger.error("Analytics compare failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Analytics error: {exc}")

    if not result.all_fact_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data found for metric '{request.metric}' "
                f"in the requested entities/period range. "
                f"Ensure documents have been ingested and processed (Phase 2)."
            ),
        )

    # Serialise dataclasses → Pydantic
    return AnalyticsCompareResponse(
        metric=result.metric,
        unit=result.unit,
        period_start_year=result.period_start_year,
        period_end_year=result.period_end_year,
        entities=[_entity_analytics_to_schema(e) for e in result.entities],
        anomalies=[_anomaly_to_schema(a) for a in result.anomalies],
        all_fact_ids=result.all_fact_ids,
    )


# ---------------------------------------------------------------------------
# POST /analytics/trend
# ---------------------------------------------------------------------------

@router.post(
    "/trend",
    response_model=AnalyticsTrendResponse,
    summary="Time series for a single entity/metric — suitable for charting",
    description=(
        "Pure deterministic analytics — no LLM. "
        "Each data point carries its source fact_id, conflict status, and flag status."
    ),
)
async def trend(
    request: AnalyticsTrendRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await analytics_service.get_trend(
            db=db,
            entity_id=request.entity_id,
            metric=request.metric,
            start_year=request.period_start_year,
            end_year=request.period_end_year,
        )
    except Exception as exc:
        logger.error("Analytics trend failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Analytics error: {exc}")

    if not result.all_fact_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data found for entity '{request.entity_id}' / "
                f"metric '{request.metric}' in the requested period range."
            ),
        )

    return AnalyticsTrendResponse(
        entity_id=result.entity_id,
        entity_name=result.entity_name,
        metric=result.metric,
        unit=result.unit,
        series=[_data_point_to_schema(dp) for dp in result.series],
        all_fact_ids=result.all_fact_ids,
    )


# ---------------------------------------------------------------------------
# POST /analytics/why-did-this-change
# ---------------------------------------------------------------------------

@router.post(
    "/why-did-this-change",
    response_model=WhyChangeResponse,
    summary="Why-Did-This-Change — document-grounded explanation with citation enforcement",
    description=(
        "5-step pipeline: compute change → semantic retrieval → LLM citation analysis → "
        "classify (document-supported | data-derived | insufficient-evidence) → package. "
        "The LLM cannot invent explanations; all responses go through a 4-layer "
        "insufficient-evidence enforcement stack."
    ),
)
async def why_did_this_change(
    request: WhyChangeRequest,
    db: AsyncSession = Depends(get_db),
):
    # Resolve entity name for the search query
    entity_res = await db.execute(
        select(CanonicalEntity).where(CanonicalEntity.id == request.entity_id)
    )
    entity = entity_res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {request.entity_id} not found.")

    query_id = uuid.uuid4()

    try:
        why_result = await run_why_change(
            db=db,
            entity_id=request.entity_id,
            entity_name=entity.canonical_name,
            metric=request.metric,
            period_year=request.period_year,
            top_k=request.top_k_semantic,
        )
    except Exception as exc:
        logger.error("Why-change engine failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Why-change error: {exc}")

    # Build conflict info
    conflicts = await get_open_conflicts_for_facts(db, why_result.all_fact_ids)

    # Calculation string
    if why_result.from_value is not None and why_result.to_value is not None:
        calculation = (
            f"Change = ({why_result.to_value} - {why_result.from_value}) / "
            f"{why_result.from_value} × 100 = {why_result.pct_change or 0:.1f}%"
        )
    else:
        calculation = None

    # Build the answer text
    if why_result.classification == "insufficient-evidence":
        answer = (
            f"No sufficient evidence found in the available documents to explain the "
            f"change in {request.metric.replace('_', ' ')} for {entity.canonical_name} "
            f"in {request.period_year}. "
            f"No documented explanation was found in the available sources."
        )
    elif why_result.classification == "data-derived":
        answer = (
            f"{entity.canonical_name} {request.metric.replace('_', ' ')} "
            f"changed by {why_result.pct_change or 0:.1f}% in {request.period_year}. "
            f"This represents a trend pattern visible in the data, but no explicit "
            f"textual explanation was found in the ingested documents."
        )
        if calculation:
            answer = f"Calculated: {calculation}. {answer}"
    else:
        # document-supported: use LLM explanation
        answer = why_result.llm_explanation or (
            f"{entity.canonical_name} {request.metric.replace('_', ' ')} changed by "
            f"{why_result.pct_change or 0:.1f}% in {request.period_year} "
            f"(documented explanation found in retrieved sources)."
        )

    # Package
    base_response = await package_response(
        db=db,
        query_id=query_id,
        question=f"Why did {entity.canonical_name} {request.metric} change in {request.period_year}?",
        answer=answer,
        fact_ids=why_result.all_fact_ids,
        conflicts=conflicts,
        reasoning_type=why_result.classification,  # type: ignore[arg-type]
        calculation=calculation,
        tasks_planned=1,
        tasks_with_results=1 if why_result.from_value is not None else 0,
    )

    # Build why_change_detail
    why_detail = WhyChangeDetail(
        from_value=why_result.from_value,
        to_value=why_result.to_value,
        pct_change=why_result.pct_change,
        fact_id_from=why_result.fact_id_from,
        fact_id_to=why_result.fact_id_to,
        classification=why_result.classification,  # type: ignore[arg-type]
        cited_passages=[
            CitedPassage(
                document_id=cp.document_id,
                document_filename=cp.document_filename,
                page_number=cp.page_number,
                excerpt=cp.excerpt,
            )
            for cp in why_result.cited_passages
        ],
    )

    return WhyChangeResponse(
        **base_response.model_dump(),
        why_change_detail=why_detail,
    )


# ---------------------------------------------------------------------------
# Schema converters
# ---------------------------------------------------------------------------

def _data_point_to_schema(dp) -> AnalyticsDataPoint:
    return AnalyticsDataPoint(
        period_label=dp.period_label,
        period_start=dp.period_start,
        period_end=dp.period_end,
        value=dp.value,
        fact_id=dp.fact_id,
        has_conflict=dp.has_conflict,
        has_flag=dp.has_flag,
    )


def _entity_analytics_to_schema(e) -> EntityAnalytics:
    from app.schemas.query import YoYChange as YoYChangeSchema
    return EntityAnalytics(
        entity_id=e.entity_id,
        entity_name=e.entity_name,
        data_points=[_data_point_to_schema(dp) for dp in e.data_points],
        yoy_changes=[
            YoYChangeSchema(
                from_period=yoy.from_period,
                to_period=yoy.to_period,
                absolute_change=yoy.absolute_change,
                pct_change=yoy.pct_change,
                fact_ids_used=yoy.fact_ids_used,
            )
            for yoy in e.yoy_changes
        ],
        cagr_pct=e.cagr_pct,
        cagr_fact_ids=e.cagr_fact_ids,
    )


def _anomaly_to_schema(a) -> AnomalyPoint:
    return AnomalyPoint(
        entity_id=a.entity_id,
        period_label=a.period_label,
        fact_id=a.fact_id,
        value=a.value,
        mean=a.mean,
        std_dev=a.std_dev,
        z_score=a.z_score,
        note=a.note,
    )
