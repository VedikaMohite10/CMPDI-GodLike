"""Pydantic schemas for validation flags endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ValidationFlagDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     uuid.UUID
    flag_type:              str
    severity:               str
    detail:                 dict
    status:                 str
    detected_at:            datetime
    # Joined from normalized_fact + extracted_fact + document
    normalized_fact_id:     uuid.UUID
    metric:                 Optional[str]   = None
    normalized_value:       Optional[float] = None
    normalized_unit:        Optional[str]   = None
    canonical_entity_name:  Optional[str]   = None
    document_id:            Optional[uuid.UUID] = None
    document_filename:      Optional[str]   = None
    page_number:            Optional[int]   = None
