"""Phase 3 Pydantic schemas — request/response models for the AI Copilot and Analytics endpoints.

All AI-influenced responses must use ExplainableAIResponse as their outermost envelope.
Pure analytics endpoints (compare, trend) use their own dedicated response models.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """A single piece of evidence backing an AI response — traceable to a source document."""
    fact_id:              uuid.UUID
    document_id:          uuid.UUID
    document_filename:    str
    page_number:          Optional[int]      = None
    excerpt:              str                = ""
    source_type:          str                = "unknown"  # "table" | "block" | "semantic"
    extraction_confidence: Optional[float]   = None


class ConflictSurfaced(BaseModel):
    """An open data conflict that was detected while retrieving facts for this response."""
    conflict_id:  uuid.UUID
    fact_a_id:    uuid.UUID
    fact_b_id:    uuid.UUID
    description:  str
    delta_pct:    Optional[float] = None
    status:       str             = "open"


# ---------------------------------------------------------------------------
# Standard Explainable AI response envelope
# Every endpoint that involves an LLM-influenced answer routes through this.
# ---------------------------------------------------------------------------

ReasoningType = Literal[
    "document-supported",
    "data-derived",
    "model-inference",
    "insufficient-evidence",
]


class ExplainableAIResponse(BaseModel):
    """Standard output shape for all AI-influenced answers in Phase 3.

    Design contract:
    - answer: Natural-language text produced by the synthesis LLM, grounded in evidence/calc.
    - evidence: Every normalized_fact that contributed to the answer, with full provenance.
    - conflicts_surfaced: Any open conflicts touching the retrieved facts — never silently ignored.
    - calculation: Human-readable description of arithmetic performed by the Analytics Service.
    - confidence: Deterministic score [0–100] computed from extraction/validation signals.
    - reasoning_type: Classification of how the answer was derived.
    """
    query_id:           uuid.UUID
    question:           str
    answer:             str
    evidence:           List[EvidenceItem]       = Field(default_factory=list)
    conflicts_surfaced: List[ConflictSurfaced]   = Field(default_factory=list)
    calculation:        Optional[str]            = None
    confidence:         int                      = Field(ge=0, le=100)
    reasoning_type:     ReasoningType
    analytics_results:  Optional[Dict[str, Any]] = None
    created_at:         datetime


# ---------------------------------------------------------------------------
# /query endpoint
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question:          str  = Field(..., min_length=3, max_length=2000)
    top_k_semantic:    int  = Field(default=10, ge=1, le=50)


class QueryResponseAudit(ExplainableAIResponse):
    """Extended response returned by GET /query/{id} — includes model audit fields."""
    model_used_intent:    Optional[str] = None
    model_used_synthesis: Optional[str] = None
    intent_plan:          Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Analytics — Compare
# ---------------------------------------------------------------------------

class AnalyticsDataPoint(BaseModel):
    period_label:  str
    period_start:  Optional[date] = None
    period_end:    Optional[date] = None
    value:         Optional[float]
    fact_id:       Optional[uuid.UUID]
    has_conflict:  bool = False
    has_flag:      bool = False


class YoYChange(BaseModel):
    from_period:      str
    to_period:        str
    absolute_change:  Optional[float]
    pct_change:       Optional[float]
    fact_ids_used:    List[uuid.UUID] = Field(default_factory=list)


class AnomalyPoint(BaseModel):
    entity_id:    uuid.UUID
    period_label: str
    fact_id:      Optional[uuid.UUID]
    value:        Optional[float]
    mean:         float
    std_dev:      float
    z_score:      float
    note:         str


class EntityAnalytics(BaseModel):
    entity_id:    uuid.UUID
    entity_name:  str
    data_points:  List[AnalyticsDataPoint] = Field(default_factory=list)
    yoy_changes:  List[YoYChange]          = Field(default_factory=list)
    cagr_pct:     Optional[float]          = None
    cagr_fact_ids: List[uuid.UUID]         = Field(default_factory=list)


class AnalyticsCompareRequest(BaseModel):
    entity_ids:        List[uuid.UUID] = Field(..., min_length=1, max_length=10)
    metric:            str
    period_start_year: Optional[int]  = None
    period_end_year:   Optional[int]  = None
    unit:              Optional[str]  = None


class AnalyticsCompareResponse(BaseModel):
    metric:            str
    unit:              Optional[str]
    period_start_year: Optional[int]
    period_end_year:   Optional[int]
    entities:          List[EntityAnalytics]  = Field(default_factory=list)
    anomalies:         List[AnomalyPoint]     = Field(default_factory=list)
    all_fact_ids:      List[uuid.UUID]        = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Analytics — Trend
# ---------------------------------------------------------------------------

class AnalyticsTrendRequest(BaseModel):
    entity_id:         uuid.UUID
    metric:            str
    period_start_year: Optional[int] = None
    period_end_year:   Optional[int] = None


class AnalyticsTrendResponse(BaseModel):
    entity_id:    uuid.UUID
    entity_name:  str
    metric:       str
    unit:         Optional[str]
    series:       List[AnalyticsDataPoint] = Field(default_factory=list)
    all_fact_ids: List[uuid.UUID]          = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Why-Did-This-Change
# ---------------------------------------------------------------------------

class CitedPassage(BaseModel):
    document_id:   uuid.UUID
    document_filename: str
    page_number:   Optional[int]
    excerpt:       str


class WhyChangeDetail(BaseModel):
    from_value:    Optional[float]
    to_value:      Optional[float]
    pct_change:    Optional[float]
    fact_id_from:  Optional[uuid.UUID]
    fact_id_to:    Optional[uuid.UUID]
    classification: Literal[
        "document-supported", "data-derived", "insufficient-evidence"
    ]
    cited_passages: List[CitedPassage] = Field(default_factory=list)


class WhyChangeRequest(BaseModel):
    entity_id:      uuid.UUID
    metric:         str
    period_year:    int  = Field(..., ge=2000, le=2100)
    top_k_semantic: int  = Field(default=10, ge=1, le=50)


class WhyChangeResponse(ExplainableAIResponse):
    """Why-change response extends the standard envelope with change-specific detail."""
    why_change_detail: Optional[WhyChangeDetail] = None
