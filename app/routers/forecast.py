"""Forecasting router — Phase 5.

POST /forecast              — run a forecast (analyst+)
GET  /forecast/{id}         — retrieve a stored forecast by ID (analyst+)
GET  /forecast              — list recent forecasts for an entity/metric (analyst+)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2 import CanonicalEntity
from app.models.phase5 import ForecastResult, User
from app.services.auth.dependencies import get_current_user
from app.services.forecast.forecast_service import (
    InsufficientDataResponse,
    ForecastResponse,
    run_forecast,
)

router = APIRouter(prefix="/forecast", tags=["Forecasting Engine"])


class ForecastRequest(BaseModel):
    entity_id:     uuid.UUID
    metric:        str
    horizon_years: int = 3

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "<uuid of canonical entity>",
                "metric":    "coal_production",
                "horizon_years": 3,
            }
        }


def _serialize_forecast_result(r: ForecastResult) -> dict:
    return {
        "id":                    str(r.id),
        "forecast_type":         r.forecast_type,   # always "Model-based forecast"
        "entity_id":             str(r.entity_id),
        "metric":                r.metric,
        "horizon_years":         r.horizon_years,
        "model_used":            r.model_used,
        "escalation_reason":     r.escalation_reason,
        "training_period_start": r.training_period_start.isoformat() if r.training_period_start else None,
        "training_period_end":   r.training_period_end.isoformat() if r.training_period_end else None,
        "training_data_points":  r.training_data_points,
        "forecast_data":         r.forecast_data,
        "data_quality_summary":  r.data_quality_summary,
        "insufficient_data":     r.insufficient_data,
        "insufficient_reason":   r.insufficient_reason,
        "created_at":            r.created_at.isoformat(),
    }


@router.post(
    "",
    summary="Run a forecast for an entity/metric (analyst+)",
    description=(
        "Assesses historical data sufficiency, selects an appropriate model "
        "(moving average → exponential smoothing → ARIMA), and returns a labeled forecast. "
        "Every response carries 'forecast_type: \"Model-based forecast\"' at the JSON root. "
        "Returns an insufficient_historical_data response if the data gate is not met."
    ),
)
async def forecast(
    req: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if req.horizon_years < 1 or req.horizon_years > 10:
        raise HTTPException(status_code=400, detail="horizon_years must be between 1 and 10.")

    try:
        result = await run_forecast(
            entity_id=req.entity_id,
            metric=req.metric,
            horizon_years=req.horizon_years,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {exc}")

    # Both success and insufficient-data cases carry forecast_type at root
    if isinstance(result, InsufficientDataResponse):
        return {
            "forecast_type":              result.forecast_type,
            "insufficient_historical_data": result.insufficient_historical_data,
            "entity_id":                  result.entity_id,
            "metric":                     result.metric,
            "available_points":           result.available_points,
            "required_points":            result.required_points,
            "missing_period_ratio":       result.missing_period_ratio,
            "reason":                     result.reason,
        }

    # Success case
    return {
        "forecast_type":         result.forecast_type,    # "Model-based forecast" — always present
        "entity_id":             result.entity_id,
        "entity_name":           result.entity_name,
        "metric":                result.metric,
        "horizon_years":         result.horizon_years,
        "model_used":            result.model_used,
        "escalation_reason":     result.escalation_reason,
        "training_period_start": result.training_period_start,
        "training_period_end":   result.training_period_end,
        "training_data_points":  result.training_data_points,
        "forecast_points": [
            {
                "year":        fp.year,
                "predicted":   fp.predicted,
                "lower_bound": fp.lower_bound,
                "upper_bound": fp.upper_bound,
            }
            for fp in result.forecast_points
        ],
        "unit":                  result.unit,
        "assumptions":           result.assumptions,
        "data_quality_summary":  result.data_quality_summary,
        "stored_result_id":      result.stored_result_id,
    }


@router.get(
    "/{forecast_id}",
    summary="Retrieve a stored forecast by ID (analyst+)",
)
async def get_forecast_by_id(
    forecast_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ForecastResult).where(ForecastResult.id == forecast_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found.")
    return _serialize_forecast_result(record)


@router.get(
    "",
    summary="List recent forecasts for an entity/metric (analyst+)",
)
async def list_forecasts(
    entity_id: Optional[uuid.UUID] = Query(None),
    metric:    Optional[str]       = Query(None),
    limit:     int                 = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = []
    if entity_id:
        filters.append(ForecastResult.entity_id == entity_id)
    if metric:
        filters.append(ForecastResult.metric.ilike(f"%{metric}%"))

    result = await db.execute(
        select(ForecastResult)
        .where(*filters)
        .order_by(ForecastResult.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return {
        "total": len(records),
        "forecasts": [_serialize_forecast_result(r) for r in records],
    }
