"""Entities router — GET /entities, GET /entities/{id}."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase2 import CanonicalEntity, EntityAlias, NormalizedFact
from app.schemas.common import PaginatedResponse
from app.schemas.entities import CanonicalEntitySummary, CanonicalEntityDetail

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("", response_model=PaginatedResponse)
async def list_entities(
    entity_type: Optional[str] = Query(None),
    page:        int            = Query(1, ge=1),
    page_size:   int            = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = []
    if entity_type:
        filters.append(CanonicalEntity.entity_type == entity_type)

    total_res = await db.execute(
        select(func.count()).select_from(CanonicalEntity).where(*filters)
    )
    total = total_res.scalar_one()

    result = await db.execute(
        select(CanonicalEntity)
        .where(*filters)
        .order_by(CanonicalEntity.canonical_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    entities = result.scalars().all()

    items = []
    for e in entities:
        alias_count_res = await db.execute(
            select(func.count()).select_from(EntityAlias)
            .where(EntityAlias.canonical_entity_id == e.id)
        )
        fact_count_res = await db.execute(
            select(func.count()).select_from(NormalizedFact)
            .where(NormalizedFact.canonical_entity_id == e.id)
        )
        items.append(CanonicalEntitySummary(
            id=e.id, canonical_name=e.canonical_name, entity_type=e.entity_type,
            description=e.description,
            alias_count=alias_count_res.scalar_one(),
            fact_count=fact_count_res.scalar_one(),
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{entity_id}", response_model=CanonicalEntityDetail)
async def get_entity(entity_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CanonicalEntity).where(CanonicalEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found.")

    alias_res = await db.execute(
        select(EntityAlias).where(EntityAlias.canonical_entity_id == entity.id)
        .order_by(EntityAlias.confidence.desc())
    )
    aliases = alias_res.scalars().all()

    # Fact summary
    fact_count_res = await db.execute(
        select(func.count()).select_from(NormalizedFact)
        .where(NormalizedFact.canonical_entity_id == entity.id)
    )
    metrics_res = await db.execute(
        select(NormalizedFact.metric, func.count().label("n"))
        .where(NormalizedFact.canonical_entity_id == entity.id)
        .group_by(NormalizedFact.metric)
        .order_by(func.count().desc())
    )
    metrics_list = [row.metric for row in metrics_res.all() if row.metric]

    return CanonicalEntityDetail(
        id=entity.id,
        canonical_name=entity.canonical_name,
        entity_type=entity.entity_type,
        description=entity.description,
        created_at=entity.created_at,
        aliases=list(aliases),
        fact_summary={"total_facts": fact_count_res.scalar_one(), "metrics": metrics_list},
    )
