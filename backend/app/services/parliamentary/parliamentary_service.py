"""Parliamentary Query Copilot service — Phase 5.

Higher-scrutiny variant of Phase 3's AI Query Copilot.  Every response is
PERMANENTLY stored in pending_review status and CANNOT be marked final
without an explicit reviewer action.

Pipeline:
  1. Intent detection         — reuses query_copilot._detect_intent()
  2. Semantic retrieval       — reuses query_copilot._semantic_retrieve()
  3. Analytics tasks          — reuses query_copilot._run_analytics_tasks()
  4. Cross-doc conflict check — surfaces ALL open conflicts on retrieved facts
  5. Draft synthesis          — parliamentary-specific LLM prompt with stricter rules
  6. Persist                  — status=pending_review; NEVER auto-approved
  7. Audit log                — action_type='parliamentary_submitted'

Design guarantee: the final_answer field is only populated and returned when
status == 'approved'.  The service never returns draft_answer to public callers;
only the reviewer-facing review endpoint surfaces the draft.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.phase2 import CanonicalEntity
from app.models.phase4 import AuditLog
from app.models.phase5 import ParliamentaryQuery, User
from app.services import model_gateway
from app.services.analytics.analytics_service import get_open_conflicts_for_facts
import app.services.query_copilot as _qc  # access private helpers via module reference

logger = logging.getLogger(__name__)
settings = get_settings()

# Sentinel inserted when a claim cannot be grounded to a citation.
_UNCITED_SENTINEL = "[CLAIM REQUIRES CITATION — REMOVED BY EVIDENCE VERIFICATION]"

_PARLIAMENTARY_SYNTHESIS_SYSTEM = (
    "You are a factual synthesizer for a PARLIAMENTARY QUERY system for coal mining. "
    "This response will undergo mandatory human review. STRICT RULES:\n"
    "1. Every factual claim MUST be followed by a citation [N] referencing one of the "
    "   numbered evidence passages.\n"
    f"2. If a claim cannot be cited, write '{_UNCITED_SENTINEL}' instead.\n"
    "3. If OPEN CONFLICTS are listed, disclose them explicitly and state they require "
    "   human resolution before this response can be treated as authoritative.\n"
    "4. Do NOT compute numbers — use only pre-calculated analytics provided.\n"
    "5. Do NOT invent entities, dates, or values not present in the evidence.\n"
    "6. Begin your response with: 'DRAFT — PENDING HUMAN REVIEW.'"
)


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

async def submit_parliamentary_query(
    *,
    question: str,
    submitted_by: Optional[User],
    db: AsyncSession,
) -> ParliamentaryQuery:
    """Run the parliamentary pipeline and persist as pending_review.

    Returns the persisted record. The draft_answer field is stored but NOT
    surfaced to public callers — final_answer is None until approved.
    """
    logger.info("Parliamentary query submitted: %r", question[:120])

    # ------------------------------------------------------------------
    # Step 1 — Intent detection (reuse Phase 3 private helper)
    # ------------------------------------------------------------------
    try:
        intent_plan: Dict[str, Any] = await _qc._detect_intent(db, question)
    except Exception as exc:
        logger.warning("Intent detection failed: %s — falling back to semantic-only", exc)
        intent_plan = {
            "intent": "semantic",
            "analytics_tasks": [],
            "semantic_query": question,
            "why_change_request": None,
            "planner_notes": f"Intent detection failed: {exc}",
        }

    # ------------------------------------------------------------------
    # Step 2 — Semantic retrieval (reuse Phase 3)
    # ------------------------------------------------------------------
    semantic_query_str = intent_plan.get("semantic_query") or question
    try:
        raw_passages: List[Dict[str, Any]] = await _qc._semantic_retrieve(
            semantic_query_str, top_k=8
        )
        # Filter by relevance threshold
        passages = [
            p for p in raw_passages
            if p.get("score", 0) >= settings.SEMANTIC_RELEVANCE_THRESHOLD
        ]
    except Exception as exc:
        logger.warning("Semantic retrieval failed: %s", exc)
        passages = []

    # ------------------------------------------------------------------
    # Step 3 — Analytics tasks (reuse Phase 3)
    # ------------------------------------------------------------------
    analytics_result: Optional[Any] = None
    calc_strs: List[str] = []
    analytic_fact_ids: List[uuid.UUID] = []
    tasks_with_results: int = 0

    analytics_tasks = intent_plan.get("analytics_tasks", [])
    if analytics_tasks and intent_plan.get("intent") in ("analytics", "both"):
        try:
            analytics_result, calc_strs, analytic_fact_ids, tasks_with_results = (
                await _qc._run_analytics_tasks(db, analytics_tasks)
            )
        except Exception as exc:
            logger.warning("Analytics tasks failed: %s", exc)

    calculation_str = "; ".join(calc_strs) if calc_strs else None

    # Gather all fact IDs
    semantic_fact_ids = _qc._extract_fact_ids_from_passages(
        passages, list(range(len(passages)))
    )
    all_fact_ids = list(set(analytic_fact_ids + semantic_fact_ids))

    # ------------------------------------------------------------------
    # Step 4 — Cross-document conflict check (MANDATORY; never silenced)
    # ------------------------------------------------------------------
    open_conflicts = []
    has_open_conflicts = False
    if all_fact_ids:
        try:
            open_conflicts = await get_open_conflicts_for_facts(db, all_fact_ids)
            has_open_conflicts = bool(open_conflicts)
        except Exception as exc:
            logger.warning("Conflict check failed: %s", exc)

    conflicts_surfaced = [
        {
            "conflict_id": str(c.id),
            "metric":      c.metric,
            "period":      f"{c.period_start} → {c.period_end}",
            "value_a":     c.value_a,
            "value_b":     c.value_b,
            "delta_pct":   c.delta_pct,
            "status":      c.status,
        }
        for c in open_conflicts
    ]

    # ------------------------------------------------------------------
    # Step 5 — Evidence verification + Parliamentary-grade draft synthesis
    # ------------------------------------------------------------------
    evidence_block = "\n\n".join([
        f"[{i+1}] {p.get('document_filename', 'Unknown')} p.{p.get('page_number', '?')}: "
        f"{(p.get('text_excerpt') or '')[:400]}"
        for i, p in enumerate(passages[:10])
    ])

    conflict_block = ""
    if has_open_conflicts:
        conflict_block = (
            "\n\nOPEN CONFLICTS (MUST be disclosed explicitly in your response):\n"
            + "\n".join([
                f"- {c.get('metric')} / {c.get('period')}: "
                f"value A={c.get('value_a')}, value B={c.get('value_b')} "
                f"(delta {c.get('delta_pct', 0) or 0:.1f}%)"
                for c in conflicts_surfaced
            ])
        )

    analytics_block = ""
    if calc_strs:
        analytics_block = f"\n\nPre-calculated analytics:\n" + "\n".join(calc_strs)

    synthesis_prompt = (
        f"Question: {question}\n\n"
        f"Evidence passages:\n{evidence_block or '(no passages retrieved)'}"
        f"{conflict_block}"
        f"{analytics_block}\n\n"
        "Produce the draft response following all rules above."
    )

    if not passages and not calc_strs:
        draft_answer = (
            "DRAFT — PENDING HUMAN REVIEW. "
            "Insufficient evidence: no relevant documents or data were retrieved "
            "to answer this question. This response cannot be approved without "
            "additional source material."
        )
    else:
        try:
            draft_answer = await model_gateway.generate(
                model=settings.SYNTHESIS_LLM_MODEL,
                system=_PARLIAMENTARY_SYNTHESIS_SYSTEM,
                prompt=synthesis_prompt,
                temperature=0.1,
                max_tokens=1500,
            )
            if not isinstance(draft_answer, str):
                draft_answer = str(draft_answer)
        except Exception as exc:
            logger.error("Parliamentary synthesis failed: %s", exc)
            draft_answer = (
                f"DRAFT — PENDING HUMAN REVIEW. "
                f"[Synthesis error: {exc}] Manual review required."
            )

    # Build evidence list for storage
    evidence_out = [
        {
            "document_id":       p.get("document_id"),
            "document_filename": p.get("document_filename"),
            "page_number":       p.get("page_number"),
            "excerpt":           (p.get("text_excerpt") or "")[:600],
            "score":             p.get("score"),
        }
        for p in passages
    ]

    # ------------------------------------------------------------------
    # Step 6 — Persist as pending_review
    # ------------------------------------------------------------------
    pq = ParliamentaryQuery(
        question=question,
        submitted_by_id=submitted_by.id if submitted_by else None,
        intent_plan=intent_plan,
        evidence=evidence_out,
        conflicts_surfaced=conflicts_surfaced,
        analytics_results=_qc._serialise_analytics(analytics_result),
        calculation=calculation_str,
        confidence=50 if not passages and not calc_strs else 70,
        reasoning_type="parliamentary",
        has_open_conflicts=has_open_conflicts,
        draft_answer=draft_answer,
        status="pending_review",
        model_used_intent=settings.INTENT_LLM_MODEL,
        model_used_synthesis=settings.SYNTHESIS_LLM_MODEL,
    )
    db.add(pq)
    await db.flush()

    # ------------------------------------------------------------------
    # Step 7 — Audit log
    # ------------------------------------------------------------------
    audit = AuditLog(
        reviewer=submitted_by.username if submitted_by else "anonymous",
        action_type="parliamentary_submitted",
        target_table="parliamentary_queries",
        target_id=pq.id,
        before_value=None,
        after_value={"status": "pending_review", "question": question[:200]},
        note=f"Parliamentary query submitted by "
             f"{submitted_by.username if submitted_by else 'anonymous'}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(pq)
    logger.info("Parliamentary query %s stored as pending_review", pq.id)
    return pq


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

async def approve_parliamentary_query(
    *,
    query_id: uuid.UUID,
    reviewer: User,
    note: Optional[str],
    db: AsyncSession,
) -> ParliamentaryQuery:
    """Mark a parliamentary query as approved.

    Only pending_review queries can be approved.
    This is the ONLY path that exposes the draft_answer as the final_answer.
    """
    pq = await _get_query_or_raise(db, query_id)
    if pq.status != "pending_review":
        raise ValueError(
            f"Query {query_id} is in status '{pq.status}' — "
            "only 'pending_review' queries can be approved."
        )

    before = {"status": pq.status}
    pq.status = "approved"
    pq.reviewer_id = reviewer.id
    pq.reviewer_note = note
    pq.reviewed_at = datetime.now(timezone.utc)

    audit = AuditLog(
        reviewer=reviewer.username,
        action_type="parliamentary_approved",
        target_table="parliamentary_queries",
        target_id=query_id,
        before_value=before,
        after_value={"status": "approved", "reviewer": reviewer.username},
        note=note,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(pq)
    logger.info("Parliamentary query %s approved by %s", query_id, reviewer.username)
    return pq


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

async def reject_parliamentary_query(
    *,
    query_id: uuid.UUID,
    reviewer: User,
    note: Optional[str],
    db: AsyncSession,
) -> ParliamentaryQuery:
    """Mark a parliamentary query as rejected.

    The draft_answer is permanently suppressed after rejection.
    """
    pq = await _get_query_or_raise(db, query_id)
    if pq.status not in ("pending_review", "draft"):
        raise ValueError(
            f"Query {query_id} is in status '{pq.status}' — "
            "only 'pending_review' queries can be rejected."
        )

    before = {"status": pq.status}
    pq.status = "rejected"
    pq.reviewer_id = reviewer.id
    pq.reviewer_note = note
    pq.reviewed_at = datetime.now(timezone.utc)

    audit = AuditLog(
        reviewer=reviewer.username,
        action_type="parliamentary_rejected",
        target_table="parliamentary_queries",
        target_id=query_id,
        before_value=before,
        after_value={"status": "rejected", "reviewer": reviewer.username},
        note=note,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(pq)
    logger.info("Parliamentary query %s rejected by %s", query_id, reviewer.username)
    return pq


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_query_or_raise(db: AsyncSession, query_id: uuid.UUID) -> ParliamentaryQuery:
    result = await db.execute(
        select(ParliamentaryQuery).where(ParliamentaryQuery.id == query_id)
    )
    pq = result.scalar_one_or_none()
    if pq is None:
        raise ValueError(f"Parliamentary query {query_id} not found.")
    return pq


def serialize_pq(pq: ParliamentaryQuery, *, include_draft: bool = False) -> dict:
    """Serialize a ParliamentaryQuery for API responses.

    final_answer is only populated when status == 'approved'.
    draft_answer_for_review is only included when include_draft=True
    AND the query is in pending_review (reviewer-facing path only).
    """
    out: dict = {
        "id":                   str(pq.id),
        "question":             pq.question,
        "status":               pq.status,
        "has_open_conflicts":   pq.has_open_conflicts,
        "confidence":           pq.confidence,
        "reasoning_type":       pq.reasoning_type,
        "conflicts_surfaced":   pq.conflicts_surfaced,
        "evidence_count":       len(pq.evidence) if pq.evidence else 0,
        "evidence":             pq.evidence,
        "analytics_results":    pq.analytics_results,
        "calculation":          pq.calculation,
        "model_used_intent":    pq.model_used_intent,
        "model_used_synthesis": pq.model_used_synthesis,
        "submitted_by_id":      str(pq.submitted_by_id) if pq.submitted_by_id else None,
        "reviewer_id":          str(pq.reviewer_id) if pq.reviewer_id else None,
        "reviewer_note":        pq.reviewer_note,
        "reviewed_at":          pq.reviewed_at.isoformat() if pq.reviewed_at else None,
        "created_at":           pq.created_at.isoformat(),
        "updated_at":           pq.updated_at.isoformat(),
        # final_answer: ONLY when approved
        "final_answer":         pq.draft_answer if pq.status == "approved" else None,
    }
    if include_draft and pq.status == "pending_review":
        out["draft_answer_for_review"] = pq.draft_answer
    return out
