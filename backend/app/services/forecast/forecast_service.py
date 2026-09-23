"""Forecasting Engine — Phase 5.

Implements the model-escalation ladder:
  1. Moving average (window=3) — baseline, always tried first
  2. Exponential smoothing (SES/Holt via statsmodels) — if trend detected
  3. ARIMA (limited grid via statsmodels) — if seasonality or SES inadequate

Before any model runs, a data-sufficiency gate enforces:
  - >= 5 distinct annual data points
  - <= 50% missing periods in the observed span

Every forecast response carries:
  - forecast_type: "Model-based forecast"  (mandatory, at JSON root)
  - model_used, escalation_reason, training_period
  - predicted_values with lower/upper bounds
  - data_quality_summary
  - assumptions list

Design guarantee: the string "Model-based forecast" appears at the top level
of every ForecastResponse so that any consuming system (report generator, UI,
parliamentary copilot) cannot accidentally omit it.
"""
from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import CanonicalEntity, NormalizedFact, ExtractedFact, Conflict
from app.models.phase5 import ForecastResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / escalation thresholds
# ---------------------------------------------------------------------------

MIN_DATA_POINTS = 5          # Absolute minimum to attempt any model
MAX_MISSING_RATIO = 0.50     # If > 50% of years in span are missing → insufficient
TREND_R2_THRESHOLD = 0.60    # Pearson r² threshold to escalate MA → SES
MIN_POINTS_FOR_SES = 7       # Need ≥7 points before trying SES
MIN_POINTS_FOR_ARIMA = 8     # Need ≥8 points before trying ARIMA
SES_ARIMA_RMSE_RATIO = 1.20  # Escalate SES→ARIMA if holdout RMSE ratio > 1.20
MA_WINDOW = 3


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ForecastPoint:
    year:        int
    predicted:   float
    lower_bound: float
    upper_bound: float


@dataclass
class InsufficientDataResponse:
    """Returned when the data-sufficiency gate is not met."""
    insufficient_historical_data: bool = True
    forecast_type:                str  = "Model-based forecast"
    entity_id:    Optional[str]   = None
    metric:       Optional[str]   = None
    available_points: int         = 0
    required_points:  int         = MIN_DATA_POINTS
    missing_period_ratio: float   = 0.0
    reason:       str             = ""


@dataclass
class ForecastResponse:
    """Full forecast package — every field documented for transparency."""
    forecast_type:         str   = "Model-based forecast"   # MANDATORY — always present
    entity_id:             str   = ""
    entity_name:           str   = ""
    metric:                str   = ""
    horizon_years:         int   = 1
    model_used:            str   = ""
    escalation_reason:     str   = "baseline_sufficient"
    training_period_start: Optional[str] = None
    training_period_end:   Optional[str] = None
    training_data_points:  int   = 0
    forecast_points:       List[ForecastPoint] = field(default_factory=list)
    unit:                  str   = ""
    assumptions:           List[str] = field(default_factory=list)
    data_quality_summary:  Dict[str, Any] = field(default_factory=dict)
    stored_result_id:      Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_forecast(
    *,
    entity_id: uuid.UUID,
    metric: str,
    horizon_years: int,
    db: AsyncSession,
) -> ForecastResponse | InsufficientDataResponse:
    """Assess data sufficiency and run the appropriate model.

    Returns ForecastResponse on success, InsufficientDataResponse if
    the historical data does not meet minimum requirements.
    """
    # ── Load entity ────────────────────────────────────────────────────────
    entity_res = await db.execute(
        select(CanonicalEntity).where(CanonicalEntity.id == entity_id)
    )
    entity = entity_res.scalar_one_or_none()
    if entity is None:
        return InsufficientDataResponse(
            entity_id=str(entity_id),
            reason=f"Entity {entity_id} not found in canonical_entities.",
        )

    # ── Load historical time series ────────────────────────────────────────
    series = await _load_series(db, entity_id, metric)

    # ── Sufficiency gate ───────────────────────────────────────────────────
    gate = _assess_sufficiency(series)
    if not gate["sufficient"]:
        return InsufficientDataResponse(
            entity_id=str(entity_id),
            metric=metric,
            available_points=gate["available_points"],
            missing_period_ratio=gate["missing_period_ratio"],
            reason=gate["reason"],
        )

    # ── Data quality summary ───────────────────────────────────────────────
    dq_summary = await _data_quality_summary(db, entity_id, metric, series)

    # ── Model selection ────────────────────────────────────────────────────
    years = [s["year"] for s in series]
    values = [s["value"] for s in series]
    unit = series[0]["unit"] if series else ""

    model_used, escalation_reason, forecast_points = _select_and_run(
        years=years, values=values, horizon_years=horizon_years
    )

    # ── Build response ─────────────────────────────────────────────────────
    assumptions = _build_assumptions(model_used, years, values)
    response = ForecastResponse(
        forecast_type="Model-based forecast",
        entity_id=str(entity_id),
        entity_name=entity.canonical_name,
        metric=metric,
        horizon_years=horizon_years,
        model_used=model_used,
        escalation_reason=escalation_reason,
        training_period_start=str(min(years)) if years else None,
        training_period_end=str(max(years)) if years else None,
        training_data_points=len(values),
        forecast_points=forecast_points,
        unit=unit,
        assumptions=assumptions,
        data_quality_summary=dq_summary,
    )

    # ── Persist ────────────────────────────────────────────────────────────
    stored_id = await _persist(db, entity_id, metric, horizon_years, response, dq_summary)
    response.stored_result_id = str(stored_id)

    return response


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

async def _load_series(
    db: AsyncSession, entity_id: uuid.UUID, metric: str
) -> List[Dict[str, Any]]:
    """Load annual time series from normalized_facts.

    Groups by period_start year, averages when multiple facts exist per year,
    and returns sorted ascending by year.
    """
    from sqlalchemy import text
    result = await db.execute(
        select(
            NormalizedFact.period_start,
            NormalizedFact.normalized_value,
            NormalizedFact.normalized_unit,
        )
        .where(and_(
            NormalizedFact.canonical_entity_id == entity_id,
            NormalizedFact.metric.ilike(f"%{metric}%"),
            NormalizedFact.normalized_value.isnot(None),
            NormalizedFact.period_start.isnot(None),
            NormalizedFact.fact_processing_status != "rejected",
        ))
        .order_by(NormalizedFact.period_start)
    )

    raw_rows = result.all()
    if not raw_rows:
        return []

    # Group by year in Python (avoids PostgreSQL GROUP BY / date_part ambiguity)
    from collections import defaultdict
    year_values: dict = defaultdict(list)
    year_units: dict = defaultdict(list)
    for row in raw_rows:
        yr = row.period_start.year
        year_values[yr].append(float(row.normalized_value))
        if row.normalized_unit:
            year_units[yr].append(row.normalized_unit)

    # Build synthetic rows as simple namespaces so the rest of the code still works
    import types
    rows = []
    for yr in sorted(year_values.keys()):
        vals = year_values[yr]
        units = year_units[yr]
        unit = max(set(units), key=units.count) if units else None
        row = types.SimpleNamespace(year=float(yr), avg_value=sum(vals)/len(vals), normalized_unit=unit)
        rows.append(row)

    # Take the most common unit
    unit_counts: Dict[str, int] = {}
    for row in rows:
        u = row.normalized_unit or ""
        unit_counts[u] = unit_counts.get(u, 0) + 1
    dominant_unit = max(unit_counts, key=unit_counts.get) if unit_counts else ""

    return [
        {"year": int(row.year), "value": float(row.avg_value), "unit": dominant_unit}
        for row in rows
        if row.avg_value is not None
    ]


# ---------------------------------------------------------------------------
# Sufficiency gate
# ---------------------------------------------------------------------------

def _assess_sufficiency(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(series)
    if n < MIN_DATA_POINTS:
        return {
            "sufficient": False,
            "available_points": n,
            "missing_period_ratio": 0.0,
            "reason": (
                f"Only {n} data point(s) available; "
                f"minimum required is {MIN_DATA_POINTS}."
            ),
        }

    years = [s["year"] for s in series]
    span = max(years) - min(years) + 1
    missing_ratio = (span - n) / span if span > 0 else 0.0

    if missing_ratio > MAX_MISSING_RATIO:
        return {
            "sufficient": False,
            "available_points": n,
            "missing_period_ratio": round(missing_ratio, 3),
            "reason": (
                f"{missing_ratio*100:.1f}% of years in the observed span "
                f"({min(years)}–{max(years)}) are missing; "
                f"maximum allowed is {MAX_MISSING_RATIO*100:.0f}%."
            ),
        }

    return {
        "sufficient": True,
        "available_points": n,
        "missing_period_ratio": round(missing_ratio, 3),
        "reason": "Data sufficiency gate passed.",
    }


# ---------------------------------------------------------------------------
# Model selection ladder
# ---------------------------------------------------------------------------

def _select_and_run(
    years: List[int],
    values: List[float],
    horizon_years: int,
) -> Tuple[str, str, List[ForecastPoint]]:
    """Apply the escalation ladder and return (model_used, escalation_reason, points)."""
    last_year = max(years)
    n = len(values)

    # ── Baseline: Moving Average ───────────────────────────────────────────
    r2 = _pearson_r2(values)
    should_escalate_to_ses = r2 >= TREND_R2_THRESHOLD and n >= MIN_POINTS_FOR_SES

    if not should_escalate_to_ses:
        points = _moving_average_forecast(years, values, horizon_years, last_year)
        return (
            "moving_average",
            "baseline_sufficient",
            points,
        )

    # ── Escalate to Exponential Smoothing ────────────────────────────────
    escalation_reason = (
        f"Monotonic trend detected (Pearson r²={r2:.3f} >= {TREND_R2_THRESHOLD}); "
        f"escalated from moving average to exponential smoothing."
    )
    try:
        ses_points, ses_holdout_rmse = _ses_forecast(years, values, horizon_years, last_year)
    except Exception as exc:
        logger.warning("SES failed (%s); falling back to MA", exc)
        return (
            "moving_average",
            f"SES failed ({exc}); fell back to moving average.",
            _moving_average_forecast(years, values, horizon_years, last_year),
        )

    # Check if we should escalate to ARIMA
    if n >= MIN_POINTS_FOR_ARIMA:
        try:
            arima_holdout_rmse = _arima_holdout_rmse(years, values)
            if ses_holdout_rmse > arima_holdout_rmse * SES_ARIMA_RMSE_RATIO:
                arima_points = _arima_forecast(years, values, horizon_years, last_year)
                return (
                    "arima",
                    (
                        f"{escalation_reason} "
                        f"SES holdout RMSE ({ses_holdout_rmse:.3f}) > "
                        f"ARIMA RMSE ({arima_holdout_rmse:.3f}) × {SES_ARIMA_RMSE_RATIO}; "
                        f"escalated to ARIMA."
                    ),
                    arima_points,
                )
        except Exception as exc:
            logger.warning("ARIMA evaluation failed (%s); staying with SES", exc)

    return ("exponential_smoothing", escalation_reason, ses_points)


# ---------------------------------------------------------------------------
# Model implementations
# ---------------------------------------------------------------------------

def _moving_average_forecast(
    years: List[int],
    values: List[float],
    horizon: int,
    last_year: int,
) -> List[ForecastPoint]:
    """Simple trailing moving average with ±1 std as the interval."""
    window = min(MA_WINDOW, len(values))
    recent = values[-window:]
    ma_val = float(np.mean(recent))
    std = float(np.std(values)) if len(values) > 1 else 0.0

    return [
        ForecastPoint(
            year=last_year + i + 1,
            predicted=round(ma_val, 4),
            lower_bound=round(ma_val - std, 4),
            upper_bound=round(ma_val + std, 4),
        )
        for i in range(horizon)
    ]


def _ses_forecast(
    years: List[int],
    values: List[float],
    horizon: int,
    last_year: int,
) -> Tuple[List[ForecastPoint], float]:
    """Holt exponential smoothing (trend-aware)."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    arr = np.array(values, dtype=float)
    model = ExponentialSmoothing(arr, trend="add", seasonal=None)
    fit = model.fit(optimized=True)
    forecast_vals = fit.forecast(horizon)
    residuals = arr - fit.fittedvalues
    std = float(np.std(residuals))

    # Holdout RMSE: last-point leave-out
    holdout_rmse = float(np.sqrt(np.mean(residuals[-3:] ** 2))) if len(residuals) >= 3 else std

    points = [
        ForecastPoint(
            year=last_year + i + 1,
            predicted=round(float(forecast_vals[i]), 4),
            lower_bound=round(float(forecast_vals[i]) - 1.96 * std, 4),
            upper_bound=round(float(forecast_vals[i]) + 1.96 * std, 4),
        )
        for i in range(horizon)
    ]
    return points, holdout_rmse


def _arima_holdout_rmse(years: List[int], values: List[float]) -> float:
    """Compute ARIMA(1,1,0) holdout RMSE for SES vs ARIMA comparison."""
    from statsmodels.tsa.arima.model import ARIMA

    arr = np.array(values, dtype=float)
    model = ARIMA(arr, order=(1, 1, 0))
    fit = model.fit()
    residuals = arr[1:] - fit.fittedvalues[1:]  # ARIMA(1,1,0) loses first obs
    return float(np.sqrt(np.mean(residuals[-3:] ** 2))) if len(residuals) >= 3 else float(np.std(arr))


def _arima_forecast(
    years: List[int],
    values: List[float],
    horizon: int,
    last_year: int,
) -> List[ForecastPoint]:
    """Auto-order ARIMA with limited grid (p,q in {0,1,2}, d in {0,1})."""
    from statsmodels.tsa.arima.model import ARIMA

    arr = np.array(values, dtype=float)
    best_aic = float("inf")
    best_fit = None

    for p in range(3):
        for d in range(2):
            for q in range(3):
                try:
                    m = ARIMA(arr, order=(p, d, q))
                    f = m.fit()
                    if f.aic < best_aic:
                        best_aic = f.aic
                        best_fit = f
                except Exception:
                    pass

    if best_fit is None:
        # Fallback to MA if ARIMA grid fails entirely
        return _moving_average_forecast(years, values, horizon, last_year)

    forecast_obj = best_fit.get_forecast(steps=horizon)
    means = forecast_obj.predicted_mean
    conf = forecast_obj.conf_int(alpha=0.05)

    return [
        ForecastPoint(
            year=last_year + i + 1,
            predicted=round(float(means[i]), 4),
            lower_bound=round(float(conf[i, 0]), 4),
            upper_bound=round(float(conf[i, 1]), 4),
        )
        for i in range(horizon)
    ]


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _pearson_r2(values: List[float]) -> float:
    """Pearson r² of values vs their index (measures monotonic trend strength)."""
    n = len(values)
    if n < 3:
        return 0.0
    x = list(range(n))
    xm = sum(x) / n
    ym = sum(values) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, values))
    den_x = math.sqrt(sum((xi - xm) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - ym) ** 2 for yi in values))
    if den_x == 0 or den_y == 0:
        return 0.0
    r = num / (den_x * den_y)
    return r ** 2


# ---------------------------------------------------------------------------
# Data quality summary
# ---------------------------------------------------------------------------

async def _data_quality_summary(
    db: AsyncSession,
    entity_id: uuid.UUID,
    metric: str,
    series: List[Dict],
) -> Dict[str, Any]:
    """Summarise data quality for the training series."""
    n = len(series)
    years = [s["year"] for s in series]
    span = max(years) - min(years) + 1 if years else 0

    # Open conflicts on this entity/metric
    conflicts_res = await db.execute(
        select(func.count()).select_from(Conflict)
        .where(and_(
            Conflict.canonical_entity_id == entity_id,
            Conflict.metric.ilike(f"%{metric}%"),
            Conflict.status == "open",
        ))
    )
    open_conflicts = int(conflicts_res.scalar_one() or 0)

    # Avg confidence
    conf_res = await db.execute(
        select(func.avg(ExtractedFact.extraction_confidence))
        .join(NormalizedFact, NormalizedFact.extracted_fact_id == ExtractedFact.id)
        .where(and_(
            NormalizedFact.canonical_entity_id == entity_id,
            NormalizedFact.metric.ilike(f"%{metric}%"),
            ExtractedFact.extraction_confidence.isnot(None),
        ))
    )
    avg_conf = conf_res.scalar_one()

    return {
        "available_points":    n,
        "observed_span_years": span,
        "missing_period_ratio": round((span - n) / span, 3) if span > 0 else 0.0,
        "open_conflicts":      open_conflicts,
        "avg_extraction_confidence": round(float(avg_conf), 4) if avg_conf else None,
        "caveats": (
            ["One or more open conflicts exist for this entity/metric — "
             "forecast may reflect conflicted source data."]
            if open_conflicts > 0 else []
        ),
    }


def _build_assumptions(model: str, years: List[int], values: List[float]) -> List[str]:
    base = [
        "Forecast is based solely on historical normalized_facts in the CMPDI database.",
        "External factors (policy changes, market conditions) are not modeled.",
        f"Training period: {min(years)}–{max(years)} ({len(values)} annual data points).",
    ]
    if model == "moving_average":
        base.append(f"Moving average window: {MA_WINDOW} years. "
                    "Assumes recent trend continues unchanged.")
    elif model == "exponential_smoothing":
        base.append("Holt exponential smoothing with additive trend. "
                    "Assumes the detected trend continues at the same rate.")
    elif model == "arima":
        base.append("ARIMA model selected via AIC-optimized grid search "
                    "(p,q ∈ {0,1,2}, d ∈ {0,1}). 95% confidence interval reported.")
    return base


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

async def _persist(
    db: AsyncSession,
    entity_id: uuid.UUID,
    metric: str,
    horizon_years: int,
    resp: ForecastResponse,
    dq_summary: Dict,
) -> uuid.UUID:
    """Store the forecast result in the forecast_results table."""
    forecast_data = {
        "years":            [fp.year for fp in resp.forecast_points],
        "predicted_values": [fp.predicted for fp in resp.forecast_points],
        "lower_bound":      [fp.lower_bound for fp in resp.forecast_points],
        "upper_bound":      [fp.upper_bound for fp in resp.forecast_points],
        "unit":             resp.unit,
        "assumptions":      resp.assumptions,
    }
    record = ForecastResult(
        entity_id=entity_id,
        metric=metric,
        horizon_years=horizon_years,
        model_used=resp.model_used,
        escalation_reason=resp.escalation_reason,
        training_period_start=(
            date(int(resp.training_period_start), 1, 1)
            if resp.training_period_start else None
        ),
        training_period_end=(
            date(int(resp.training_period_end), 12, 31)
            if resp.training_period_end else None
        ),
        training_data_points=resp.training_data_points,
        forecast_data=forecast_data,
        data_quality_summary=dq_summary,
        forecast_type="Model-based forecast",   # DB-level label enforcement
        insufficient_data=False,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record.id
