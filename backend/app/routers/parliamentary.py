"""Parliamentary Query Copilot router — Phase 5.

POST /parliamentary/query          — submit a query (analyst+)
GET  /parliamentary                — list queries with status filter (analyst+)
GET  /parliamentary/{id}           — get one query (analyst+; final_answer=null until approved)
POST /parliamentary/{id}/approve   — approve (reviewer+ only; RBAC gated)
POST /parliamentary/{id}/reject    — reject  (reviewer+ only; RBAC gated)

Key design contract:
  - 'final_answer' in GET responses is null until status == 'approved'
  - Approve/reject endpoints are the ONLY way to transition out of pending_review
  - Every approve/reject writes an audit log entry (enforced in service layer)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase5 import ParliamentaryQuery, User
from app.schemas.common import PaginatedResponse
from app.services.auth.dependencies import get_current_user, require_role
from app.services.parliamentary.parliamentary_service import (
    approve_parliamentary_query,
    reject_parliamentary_query,
    serialize_pq,
    submit_parliamentary_query,
)

router = APIRouter(prefix="/parliamentary", tags=["Parliamentary Query Copilot"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SubmitQueryRequest(BaseModel):
    question: str


class ApproveRequest(BaseModel):
    note: Optional[str] = None


class RejectRequest(BaseModel):
    note: str  # Note is required for rejection — reviewer must explain why


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a parliamentary query (analyst+)",
    description=(
        "Runs the parliamentary pipeline (intent detection → retrieval → conflict check → "
        "evidence verification → draft synthesis) and persists the result with "
        "status=pending_review. The draft answer is NOT exposed until a reviewer approves it. "
        "Requires authentication (analyst role or above)."
    ),
)
async def submit_query(
    req: SubmitQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        pq = await submit_parliamentary_query(
            question=req.question.strip(),
            submitted_by=current_user,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Parliamentary query pipeline failed: {exc}",
        )

    return {
        "message":            "Parliamentary query submitted and is now pending human review.",
        "query_id":           str(pq.id),
        "status":             pq.status,
        "has_open_conflicts": pq.has_open_conflicts,
        "evidence_count":     len(pq.evidence) if pq.evidence else 0,
        "final_answer":       None,   # ALWAYS null at submission — reviewer must approve
        "review_required":    True,
    }


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List parliamentary queries (analyst+)",
)
async def list_queries(
    query_status: Optional[str] = Query(
        None,
        alias="status",
        pattern="^(draft|pending_review|approved|rejected|all)$",
    ),
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = []
    if query_status and query_status != "all":
        filters.append(ParliamentaryQuery.status == query_status)
    elif not query_status:
        # Default: show pending_review (most actionable for reviewers)
        filters.append(ParliamentaryQuery.status == "pending_review")

    total = (await db.execute(
        select(func.count()).select_from(ParliamentaryQuery).where(*filters)
    )).scalar_one()

    rows = (await db.execute(
        select(ParliamentaryQuery)
        .where(*filters)
        .order_by(ParliamentaryQuery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    # Reviewers see draft answers; analysts see only the list summary
    is_reviewer = current_user.role in ("reviewer", "admin")

    items = [
        serialize_pq(pq, include_draft=is_reviewer)
        for pq in rows
    ]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Get one
# ---------------------------------------------------------------------------

@router.get(
    "/{query_id}",
    summary="Get a parliamentary query (analyst+)",
    description=(
        "Returns the query record. final_answer is null unless status == 'approved'. "
        "Reviewers additionally see draft_answer_for_review when status is pending_review."
    ),
)
async def get_query(
    query_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ParliamentaryQuery).where(ParliamentaryQuery.id == query_id)
    )
    pq = result.scalar_one_or_none()
    if pq is None:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found.")

    is_reviewer = current_user.role in ("reviewer", "admin")
    return serialize_pq(pq, include_draft=is_reviewer)


# ---------------------------------------------------------------------------
# Approve (reviewer+ only)
# ---------------------------------------------------------------------------

@router.post(
    "/{query_id}/approve",
    summary="Approve a parliamentary query (reviewer+ only)",
    description=(
        "Transitions status from pending_review → approved. "
        "After approval, final_answer is exposed in GET /parliamentary/{id}. "
        "Writes an audit log entry with the reviewer's identity. "
        "Requires reviewer or admin role."
    ),
)
async def approve_query(
    query_id: uuid.UUID,
    req: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    reviewer: User = Depends(require_role("reviewer", "admin")),
):
    try:
        pq = await approve_parliamentary_query(
            query_id=query_id,
            reviewer=reviewer,
            note=req.note,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message":      "Parliamentary query approved. Final answer is now publicly available.",
        "query_id":     str(pq.id),
        "status":       pq.status,
        "approved_by":  reviewer.username,
        "reviewed_at":  pq.reviewed_at.isoformat() if pq.reviewed_at else None,
        "final_answer": pq.draft_answer,   # now exposed because status == approved
    }


# ---------------------------------------------------------------------------
# Reject (reviewer+ only)
# ---------------------------------------------------------------------------

@router.post(
    "/{query_id}/reject",
    summary="Reject a parliamentary query (reviewer+ only)",
    description=(
        "Transitions status from pending_review → rejected. "
        "draft_answer is permanently suppressed. "
        "Writes an audit log entry. Requires reviewer or admin role."
    ),
)
async def reject_query(
    query_id: uuid.UUID,
    req: RejectRequest,
    db: AsyncSession = Depends(get_db),
    reviewer: User = Depends(require_role("reviewer", "admin")),
):
    try:
        pq = await reject_parliamentary_query(
            query_id=query_id,
            reviewer=reviewer,
            note=req.note,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message":     "Parliamentary query rejected. Draft answer has been suppressed.",
        "query_id":    str(pq.id),
        "status":      pq.status,
        "rejected_by": reviewer.username,
        "reviewed_at": pq.reviewed_at.isoformat() if pq.reviewed_at else None,
        "final_answer": None,   # NEVER exposed after rejection
    }
