"""Topics router — Phase 4.

GET  /topics
GET  /topics/trends
GET  /topics/{topic_id}
GET  /documents/{id}/topics   (also registered in documents router via delegation)
POST /topics/recompute
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase4 import TopicCluster
from app.schemas.topics import (
    TopicsListResponse, TopicTrendsResponse, RecomputeResponse,
    DocumentTopicsResponse, TopicOut, KeywordOut, TopicTrendOut, TopicTrendPoint,
    DocumentTopicOut,
)
from app.services.topics.topic_service import (
    get_active_topics, get_document_topics, get_topic_trends, recompute_topics,
)

router = APIRouter(tags=["Topics"])


@router.get("/topics", response_model=TopicsListResponse)
async def list_topics(db: AsyncSession = Depends(get_db)):
    """List all active discovered topics with labels and keyword summaries."""
    topics = await get_active_topics(db)
    if not topics:
        return TopicsListResponse(
            topics=[],
            algorithm="none",
            total_documents_clustered=0,
            noise_document_count=0,
            computed_at=None,
        )
    noise_docs = sum(t.document_count for t in topics if t.is_noise_cluster)
    total_docs = sum(t.document_count for t in topics)
    algorithm  = topics[0].algorithm if topics else "none"
    computed_at = max(t.computed_at for t in topics)

    topic_outs = [
        TopicOut(
            topic_id=t.id,
            label=t.label,
            document_count=t.document_count,
            top_keywords=[KeywordOut(**kw) for kw in (t.top_keywords or [])],
            is_noise_cluster=t.is_noise_cluster,
            computed_at=t.computed_at,
        )
        for t in topics
    ]
    return TopicsListResponse(
        topics=topic_outs,
        algorithm=algorithm,
        total_documents_clustered=total_docs,
        noise_document_count=noise_docs,
        computed_at=computed_at,
    )


@router.get("/topics/trends", response_model=TopicTrendsResponse)
async def topic_trends(db: AsyncSession = Depends(get_db)):
    """Topic prevalence over time (by year, derived from document report_date)."""
    raw = await get_topic_trends(db)
    items = [
        TopicTrendOut(
            topic_id=uuid.UUID(r["topic_id"]),
            label=r["label"],
            trend=[TopicTrendPoint(**p) for p in r["trend"]],
        )
        for r in raw
    ]
    return TopicTrendsResponse(topics=items)


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic(topic_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Detailed view of a single topic cluster."""
    row = await db.get(TopicCluster, topic_id)
    if not row or not row.is_active:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return TopicOut(
        topic_id=row.id,
        label=row.label,
        document_count=row.document_count,
        top_keywords=[KeywordOut(**kw) for kw in (row.top_keywords or [])],
        is_noise_cluster=row.is_noise_cluster,
        computed_at=row.computed_at,
    )


@router.get("/documents/{document_id}/topics", response_model=DocumentTopicsResponse)
async def document_topics(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Topic classification for a specific document."""
    rows = await get_document_topics(db, document_id)
    return DocumentTopicsResponse(
        document_id=document_id,
        topics=[DocumentTopicOut(**r) for r in rows],
    )


@router.post("/topics/recompute", response_model=RecomputeResponse)
async def recompute(db: AsyncSession = Depends(get_db)):
    """Trigger a full topic recomputation. Runs synchronously (may take time on large corpora)."""
    try:
        summary = await recompute_topics(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Topic recompute failed: {exc}")
    return RecomputeResponse(
        status=summary.get("status", "complete"),
        message=(
            f"Computed {summary.get('cluster_count', 0)} topic clusters "
            f"across {summary.get('document_count', 0)} documents "
            f"using {summary.get('algorithm', 'unknown')}."
        ),
    )
