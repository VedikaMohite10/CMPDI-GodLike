"""Pydantic schemas for Phase 2 facts endpoints."""
import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Extracted fact (audit/debug layer)
# ---------------------------------------------------------------------------
class ExtractedFactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    uuid.UUID
    document_id:           uuid.UUID
    page_id:               uuid.UUID
    table_id:              Optional[uuid.UUID] = None
    block_id:              Optional[uuid.UUID] = None
    raw_entity_text:       Optional[str]       = None
    raw_metric_text:       Optional[str]       = None
    raw_value:             str
    raw_unit_text:         Optional[str]       = None
    raw_date_text:         Optional[str]       = None
    extraction_method:     str
    extraction_model:      Optional[str]       = None
    llm_raw_output:        Optional[dict]      = None
    extraction_confidence: Optional[float]     = None
    is_obsolete:           bool
    created_at:            datetime


# ---------------------------------------------------------------------------
# Normalized fact — compact summary (for list views)
# ---------------------------------------------------------------------------
class NormalizedFactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                           uuid.UUID
    metric:                       Optional[str]       = None
    normalized_value:             Optional[float]     = None
    normalized_unit:              Optional[str]       = None
    period_label:                 Optional[str]       = None
    entity_resolution_method:     Optional[str]       = None
    fact_processing_status:       str
    # Joined fields (populated in router)
    canonical_entity_name:        Optional[str]       = None
    flag_count:                   int                 = 0
    has_conflict:                 bool                = False
    document_id:                  Optional[uuid.UUID] = None
    document_filename:            Optional[str]       = None
    page_number:                  Optional[int]       = None
    extraction_confidence:        Optional[float]     = None


# ---------------------------------------------------------------------------
# Source block/table in evidence response
# ---------------------------------------------------------------------------
class SourceBlock(BaseModel):
    type:          str   # 'table' | 'block'
    table:         Optional[dict] = None   # raw_structure + caption + position
    block:         Optional[dict] = None   # text + block_type + position


class PageRef(BaseModel):
    page_id:     uuid.UUID
    page_number: int


class DocumentRef(BaseModel):
    id:                uuid.UUID
    filename:          str
    original_filename: str
    storage_path:      str
    upload_date:       datetime
    report_date:       Optional[date] = None


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    flag_type:   str
    severity:    str
    detail:      dict
    status:      str
    detected_at: datetime


class AliasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias_text:        str
    resolution_method: str
    confidence:        float


class EntityRef(BaseModel):
    id:             uuid.UUID
    canonical_name: str
    entity_type:    str
    aliases:        list[AliasOut] = []


# ---------------------------------------------------------------------------
# Full evidence chain — GET /facts/{id}/evidence
# ---------------------------------------------------------------------------
class FactEvidenceResponse(BaseModel):
    fact:      dict            # all NormalizedFact fields
    extracted: ExtractedFactOut
    source:    SourceBlock
    page:      PageRef
    document:  DocumentRef
    flags:     list[FlagOut]   = []
    entity:    Optional[EntityRef] = None
