"""Human Verification Console — Review Service (Phase 4).

Implements accept / correct / reject / resolve_conflict operations.
Every action writes an audit_log entry — this is the only mutation surface.
Underlying ValidationFlag / NormalizedFact / Conflict rows are updated in-place;
the audit log captures before/after snapshots so the full change history is
reconstructable.

Design constraints:
  - Rejected facts are NEVER deleted — only their fact_processing_status is set
    to 'rejected' so they are excluded from active pipeline queries.
  - The audit_log table is append-only by convention (see model docstring).
  - The 'reviewer' field is a stub identifier (no real auth in Phase 4).
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import Conflict, NormalizedFact, ValidationFlag
from app.models.phase4 import AuditLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Flag actions
# ---------------------------------------------------------------------------

async def accept_flag(
    *,
    db: AsyncSession,
    flag_id: uuid.UUID,
    reviewer: str = "anonymous",
    note: Optional[str] = None,
) -> AuditLog:
    """Mark a validation flag as accepted (underlying value unchanged)."""
    flag = await _get_flag_or_raise(db, flag_id)
    before = {"status": flag.status}

    flag.status = "accepted"

    entry = AuditLog(
        reviewer=reviewer,
        action_type="accept",
        target_table="validation_flags",
        target_id=flag_id,
        before_value=before,
        after_value={"status": "accepted"},
        note=note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Flag %s accepted by %s", flag_id, reviewer)
    return entry


async def correct_flag(
    *,
    db: AsyncSession,
    flag_id: uuid.UUID,
    corrected_value: float,
    corrected_unit: Optional[str],
    reviewer: str = "anonymous",
    note: Optional[str] = None,
) -> AuditLog:
    """Apply a human correction to the underlying normalized_fact.

    Stores both original and corrected values in the audit log.
    Updates the normalized_fact in-place and marks the flag 'corrected'.
    """
    flag = await _get_flag_or_raise(db, flag_id)

    nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == flag.normalized_fact_id))
    nf = nf_res.scalar_one_or_none()
    if not nf:
        raise ValueError(f"NormalizedFact for flag {flag_id} not found.")

    before = {
        "flag_status":      flag.status,
        "normalized_value": nf.normalized_value,
        "normalized_unit":  nf.normalized_unit,
    }

    # Apply correction
    nf.normalized_value = corrected_value
    if corrected_unit:
        nf.normalized_unit = corrected_unit
    nf.fact_processing_status = "human_corrected"
    flag.status = "corrected"

    after = {
        "flag_status":      "corrected",
        "normalized_value": corrected_value,
        "normalized_unit":  corrected_unit or nf.normalized_unit,
    }

    entry = AuditLog(
        reviewer=reviewer,
        action_type="correct",
        target_table="normalized_facts",
        target_id=nf.id,
        before_value=before,
        after_value=after,
        note=note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Fact %s corrected by %s: %.4f → %.4f", nf.id, reviewer, before["normalized_value"] or 0, corrected_value)
    return entry


async def reject_flag(
    *,
    db: AsyncSession,
    flag_id: uuid.UUID,
    reviewer: str = "anonymous",
    note: Optional[str] = None,
) -> AuditLog:
    """Mark the flagged fact as invalid.

    The fact is soft-deleted: fact_processing_status = 'rejected'.
    It is never removed from the database — retained for audit purposes.
    """
    flag = await _get_flag_or_raise(db, flag_id)

    nf_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == flag.normalized_fact_id))
    nf = nf_res.scalar_one_or_none()

    before = {
        "flag_status":      flag.status,
        "fact_status":      nf.fact_processing_status if nf else None,
    }

    flag.status = "rejected"
    if nf:
        nf.fact_processing_status = "rejected"

    entry = AuditLog(
        reviewer=reviewer,
        action_type="reject",
        target_table="validation_flags",
        target_id=flag_id,
        before_value=before,
        after_value={"flag_status": "rejected", "fact_status": "rejected"},
        note=note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Flag %s / fact %s rejected by %s", flag_id, nf.id if nf else "?", reviewer)
    return entry


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------

VALID_RESOLUTIONS = frozenset(["fact_a_correct", "fact_b_correct", "both_valid", "neither_reliable"])


async def resolve_conflict(
    *,
    db: AsyncSession,
    conflict_id: uuid.UUID,
    resolution: str,
    canonical_value: Optional[float] = None,
    canonical_unit: Optional[str] = None,
    reviewer: str = "anonymous",
    note: str,
) -> AuditLog:
    """Record a human decision on a conflict.

    resolution must be one of:
      fact_a_correct | fact_b_correct | both_valid | neither_reliable

    If resolution is fact_a_correct or fact_b_correct and a canonical_value is
    provided, the winning fact's normalized_value is set to canonical_value.
    The losing fact (if fact_*_correct) is soft-rejected.
    """
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(
            f"Invalid resolution {resolution!r}. Must be one of: {sorted(VALID_RESOLUTIONS)}"
        )

    conflict_res = await db.execute(select(Conflict).where(Conflict.id == conflict_id))
    conflict = conflict_res.scalar_one_or_none()
    if not conflict:
        raise ValueError(f"Conflict {conflict_id} not found.")
    if conflict.status == "resolved":
        raise ValueError(f"Conflict {conflict_id} is already resolved.")

    before = {"status": conflict.status}

    conflict.status = "resolved"

    # Apply canonical value to the winning fact if specified
    winner_id: Optional[uuid.UUID] = None
    loser_id:  Optional[uuid.UUID] = None
    if resolution == "fact_a_correct":
        winner_id, loser_id = conflict.fact_a_id, conflict.fact_b_id
    elif resolution == "fact_b_correct":
        winner_id, loser_id = conflict.fact_b_id, conflict.fact_a_id

    if winner_id and canonical_value is not None:
        winner_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == winner_id))
        winner = winner_res.scalar_one_or_none()
        if winner:
            winner.normalized_value = canonical_value
            if canonical_unit:
                winner.normalized_unit = canonical_unit
            winner.fact_processing_status = "human_corrected"

    if loser_id:
        loser_res = await db.execute(select(NormalizedFact).where(NormalizedFact.id == loser_id))
        loser = loser_res.scalar_one_or_none()
        if loser:
            loser.fact_processing_status = "rejected"

    after: Dict[str, Any] = {
        "status":          "resolved",
        "resolution":      resolution,
        "canonical_value": canonical_value,
        "canonical_unit":  canonical_unit,
        "winner_fact_id":  str(winner_id) if winner_id else None,
        "loser_fact_id":   str(loser_id)  if loser_id  else None,
    }

    entry = AuditLog(
        reviewer=reviewer,
        action_type="resolve_conflict",
        target_table="conflicts",
        target_id=conflict_id,
        before_value=before,
        after_value=after,
        note=note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Conflict %s resolved (%s) by %s", conflict_id, resolution, reviewer)
    return entry


# ---------------------------------------------------------------------------
# Audit log queries
# ---------------------------------------------------------------------------

async def list_audit_log(
    *,
    db: AsyncSession,
    action_type: Optional[str] = None,
    reviewer: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 20,
):
    from sqlalchemy import func, and_
    filters = []
    if action_type:
        filters.append(AuditLog.action_type == action_type)
    if reviewer:
        filters.append(AuditLog.reviewer == reviewer)
    if target_id:
        filters.append(AuditLog.target_id == target_id)

    total_res = await db.execute(
        select(func.count()).select_from(AuditLog).where(*filters)
    )
    total = total_res.scalar_one()

    res = await db.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return res.scalars().all(), total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_flag_or_raise(db: AsyncSession, flag_id: uuid.UUID) -> ValidationFlag:
    res = await db.execute(select(ValidationFlag).where(ValidationFlag.id == flag_id))
    flag = res.scalar_one_or_none()
    if not flag:
        raise ValueError(f"ValidationFlag {flag_id} not found.")
    return flag
