"""Query router — AI Copilot endpoints.

POST /query        — main AI Query & Response Copilot
GET  /query/{id}  — retrieve a previously persisted query response (audit/debug)
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.phase2 import QueryResponse
from app.schemas.query import ExplainableAIResponse, QueryRequest, QueryResponseAudit
from app.services.query_copilot import run_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query Copilot"])


@router.post(
    "",
    response_model=ExplainableAIResponse,
    summary="AI Query & Response Copilot",
    description=(
        "Full retrieval pipeline: intent detection (7b LLM) → query planning → "
        "structured analytics retrieval → semantic retrieval → conflict validation → "
        "answer synthesis (14b LLM, strictly grounded) → Explainable AI packaging. "
        "Every number in the response originates from the deterministic Analytics Service. "
        "Open data conflicts are surfaced — never silently suppressed. "
        "Insufficient evidence is declared explicitly — the LLM never invents answers."
    ),
)
async def query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        response = await run_query(
            db=db,
            question=request.question,
            top_k_semantic=request.top_k_semantic,
        )
        return response
    except Exception as exc:
        logger.exception("Query copilot pipeline error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Query pipeline error: {exc}",
        )


@router.get(
    "/{query_id}",
    response_model=QueryResponseAudit,
    summary="Retrieve a previously generated query response",
    description=(
        "Returns a persisted query response by ID, including full audit metadata: "
        "intent plan, models used, evidence chain, conflicts surfaced, and confidence score. "
        "Use this for debugging individual responses or auditing the AI's reasoning."
    ),
)
async def get_query_response(
    query_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QueryResponse).where(QueryResponse.id == query_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Query response {query_id} not found.",
        )

    from app.schemas.query import EvidenceItem, ConflictSurfaced
    from datetime import datetime, timezone

    # Deserialise JSONB fields back to Pydantic models
    evidence = []
    for e in (record.evidence or []):
        try:
            evidence.append(EvidenceItem(**e))
        except Exception:
            pass

    conflicts = []
    for c in (record.conflicts_surfaced or []):
        try:
            conflicts.append(ConflictSurfaced(**c))
        except Exception:
            pass

    return QueryResponseAudit(
        query_id=record.id,
        question=record.question,
        answer=record.answer,
        evidence=evidence,
        conflicts_surfaced=conflicts,
        analytics_results=record.analytics_results,
        calculation=record.calculation,
        confidence=record.confidence,
        reasoning_type=record.reasoning_type,  # type: ignore[arg-type]
        created_at=record.created_at,
        model_used_intent=record.model_used_intent,
        model_used_synthesis=record.model_used_synthesis,
        intent_plan=record.intent_plan,
    )
