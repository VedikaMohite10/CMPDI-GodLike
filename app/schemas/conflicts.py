"""Pydantic schemas for conflicts endpoints."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConflictSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     uuid.UUID
    canonical_entity_name:  Optional[str]   = None
    metric:                 str
    period_label:           Optional[str]   = None   # derived from period_start/end
    value_a:                Optional[float] = None
    unit_a:                 Optional[str]   = None
    value_b:                Optional[float] = None
    unit_b:                 Optional[str]   = None
    delta_pct:              Optional[float] = None
    document_a_filename:    Optional[str]   = None
    document_b_filename:    Optional[str]   = None
    status:                 str
    detected_at:            datetime


class ConflictDetail(BaseModel):
    """Full conflict detail — both facts with complete evidence chains."""
    conflict:        dict   # all Conflict fields
    fact_a_evidence: dict   # same structure as GET /facts/{id}/evidence
    fact_b_evidence: dict
