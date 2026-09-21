"""Pydantic schemas for the Human Verification Console API (Phase 4)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Flag action requests
# ---------------------------------------------------------------------------

class FlagAcceptRequest(BaseModel):
    note:     Optional[str] = None
    reviewer: str = Field("anonymous", description="Stub reviewer ID — Phase 5 replaces with real auth")


class FlagCorrectRequest(BaseModel):
    corrected_value: float
    corrected_unit:  Optional[str] = None
    note:            Optional[str] = None
    reviewer:        str = Field("anonymous")


class FlagRejectRequest(BaseModel):
    note:     Optional[str] = None
    reviewer: str = Field("anonymous")


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------

class ConflictResolveRequest(BaseModel):
    resolution: str = Field(
        ...,
        description=(
            "One of: fact_a_correct | fact_b_correct | both_valid | neither_reliable"
        ),
    )
    canonical_value: Optional[float] = Field(
        None,
        description="Authoritative value if resolution=fact_a_correct|fact_b_correct",
    )
    canonical_unit: Optional[str] = None
    note:           str = Field(..., description="Required justification for the resolution")
    reviewer:       str = Field("anonymous")


# ---------------------------------------------------------------------------
# Audit log response
# ---------------------------------------------------------------------------

class AuditLogItemOut(BaseModel):
    id:           uuid.UUID
    timestamp:    datetime
    reviewer:     str
    action_type:  str
    target_table: str
    target_id:    uuid.UUID
    before_value: Optional[Dict[str, Any]]
    after_value:  Optional[Dict[str, Any]]
    note:         Optional[str]


class AuditLogListResponse(BaseModel):
    items:     List[AuditLogItemOut]
    total:     int
    page:      int
    page_size: int


# ---------------------------------------------------------------------------
# Generic action response
# ---------------------------------------------------------------------------

class ReviewActionResponse(BaseModel):
    status:       str
    action_type:  str
    target_id:    uuid.UUID
    audit_log_id: uuid.UUID
    message:      str
