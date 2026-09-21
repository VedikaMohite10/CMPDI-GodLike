"""Pydantic schemas for the Report Generation API (Phase 4)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ReportGenerateRequest(BaseModel):
    entity_ids:   Optional[List[uuid.UUID]] = Field(None, description="Null = all entities")
    metrics:      Optional[List[str]]       = Field(None, description="Null = all metrics")
    period_start: date
    period_end:   date
    label:        Optional[str]             = Field(None, description="Human-readable scope label")


# ---------------------------------------------------------------------------
# Internal citation / section types (also returned in API response)
# ---------------------------------------------------------------------------

class CitationOut(BaseModel):
    claim_key:             str
    normalized_fact_id:    uuid.UUID
    document_id:           uuid.UUID
    document_filename:     str
    page_number:           Optional[int]
    excerpt:               str
    extraction_confidence: Optional[float]


class NarrativeSectionOut(BaseModel):
    heading:       str
    text:          str
    citation_keys: List[str]


class TableRowOut(BaseModel):
    entity:       Optional[str]
    metric:       Optional[str]
    period:       Optional[str]
    value:        Optional[float]
    unit:         Optional[str]
    citation_key: Optional[str]


class TableSectionOut(BaseModel):
    heading: str
    rows:    List[Dict[str, Any]]


class DataPointOut(BaseModel):
    period_label:  str
    period_start:  Optional[date]
    period_end:    Optional[date]
    value:         Optional[float]
    fact_id:       Optional[uuid.UUID]
    has_conflict:  bool = False
    citation_key:  Optional[str] = None


class SeriesDataOut(BaseModel):
    entity_name:  str
    metric:       str
    unit:         Optional[str]
    data_points:  List[DataPointOut]


class TrendSectionOut(BaseModel):
    heading: str
    series:  List[SeriesDataOut]


class WarningItemOut(BaseModel):
    flag_type:          Optional[str]
    severity:           Optional[str]
    detail:             Optional[Dict[str, Any]]
    normalized_fact_id: Optional[uuid.UUID]
    entity_name:        Optional[str]
    metric:             Optional[str]


class ConflictWarningOut(BaseModel):
    conflict_id: uuid.UUID
    entity_name: Optional[str]
    metric:      str
    period:      Optional[str]
    delta_pct:   Optional[float]
    fact_a_id:   uuid.UUID
    fact_b_id:   uuid.UUID


class WarningsSectionOut(BaseModel):
    heading:        str
    open_flags:     List[WarningItemOut]
    open_conflicts: List[ConflictWarningOut]


class ReportScopeOut(BaseModel):
    entity_ids:   Optional[List[uuid.UUID]]
    metrics:      Optional[List[str]]
    period_start: date
    period_end:   date
    label:        str


# ---------------------------------------------------------------------------
# Report content (full structured output)
# ---------------------------------------------------------------------------

class ReportContentOut(BaseModel):
    report_id:             uuid.UUID
    generated_at:          datetime
    scope:                 ReportScopeOut
    executive_summary:     NarrativeSectionOut
    production_overview:   TableSectionOut
    historical_trends:     TrendSectionOut
    comparative_analysis:  TableSectionOut
    data_quality_warnings: WarningsSectionOut
    recommendations:       Optional[NarrativeSectionOut]
    citations:             List[CitationOut]
    dq_warning_count:      int
    generation_time_seconds: float
    model_used:            str


# ---------------------------------------------------------------------------
# API responses
# ---------------------------------------------------------------------------

class ReportGenerateResponse(BaseModel):
    report_id:               uuid.UUID
    status:                  str
    generation_time_seconds: float
    scope:                   ReportScopeOut
    sections:                List[str]
    citation_count:          int
    dq_warning_count:        int
    model_used:              str


class ReportListItem(BaseModel):
    report_id:               uuid.UUID
    status:                  str
    label:                   Optional[str]
    period_start:            Optional[date]
    period_end:              Optional[date]
    generation_time_seconds: Optional[float]
    created_at:              datetime
