"""Pydantic schemas for canonical entities endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AliasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    alias_text:        str
    resolution_method: str
    confidence:        float
    created_at:        datetime


class CanonicalEntitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    canonical_name: str
    entity_type:    str
    description:    Optional[str] = None
    alias_count:    int           = 0
    fact_count:     int           = 0


class CanonicalEntityDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    canonical_name: str
    entity_type:    str
    description:    Optional[str] = None
    created_at:     datetime
    aliases:        list[AliasOut] = []
    fact_summary:   dict           = {}   # {"total_facts": N, "metrics": [...]}
