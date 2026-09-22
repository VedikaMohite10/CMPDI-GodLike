"""Pydantic schemas for duplicate candidates endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DuplicateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    scope:            str
    similarity_score: float
    detection_method: str
    status:           str
    detected_at:      datetime
    # Document-scope fields
    document_a:       Optional[dict] = None   # {id, filename, upload_date}
    document_b:       Optional[dict] = None
    # Fact-scope fields
    fact_a:           Optional[dict] = None   # {id, metric, normalized_value, canonical_entity_name}
    fact_b:           Optional[dict] = None
