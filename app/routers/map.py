"""Mining Heat Map router — Phase 5.

GET /map/layers?layer=production|dispatch|resources|reserves|
               exploration|report_volume|data_quality|conflict_density
GET /map/regions/{region_id}

All endpoints require analyst+ role (any authenticated user).
Actual map rendering is a frontend concern; this API returns structured
geographic layer data only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.phase5 import User
from app.services.auth.dependencies import get_current_user
from app.services.map.map_service import VALID_LAYERS, get_layer_data, get_region_detail
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/map", tags=["Mining Heat Map"])


@router.get(
    "/layers",
    summary="Get geographic layer data (analyst+)",
    description=(
        "Returns per-region aggregated values for the requested layer. "
        "Layers: production | dispatch | resources | reserves | exploration | "
        "report_volume | data_quality | conflict_density. "
        "data_quality layer returns composite green/yellow/red buckets per region "
        "with thresholds documented verbatim in the response. "
        "Values are computed from Phase 2/3 normalized_facts — not re-implemented here."
    ),
)
async def get_layers(
    layer: str = Query(..., description=f"One of: {', '.join(VALID_LAYERS)}"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        return await get_layer_data(layer=layer, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Layer computation failed: {exc}")


@router.get(
    "/regions/{region_id}",
    summary="Drill-down detail for a region (analyst+)",
    description=(
        "Returns full detail for a single region: subsidiaries/mines in that region, "
        "production/dispatch trends (via Analytics Service), recent documents, "
        "open conflicts, data quality bucket, and average extraction confidence."
    ),
)
async def get_region(
    region_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        return await get_region_detail(region_id=region_id.upper(), db=db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Region detail failed: {exc}")
