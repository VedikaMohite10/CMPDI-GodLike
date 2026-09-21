"""Pydantic schemas for the Data Quality Dashboard API (Phase 4)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PipelineStats(BaseModel):
    documents_processed:    int
    pages_processed:        int
    tables_extracted:       int
    text_blocks_extracted:  int


class ConfidenceDistribution(BaseModel):
    high_gt_0_8:       int
    medium_0_5_to_0_8: int
    low_lt_0_5:        int


class ExtractionStats(BaseModel):
    total_extracted_facts:     int
    confidence_distribution:   ConfidenceDistribution
    low_confidence_fact_count: int
    avg_extraction_confidence: Optional[float]


class TrustStats(BaseModel):
    open_conflicts:          int
    resolved_conflicts:      int
    missing_value_flags:     int
    duplicate_candidates_open: int


class NormalizationStats(BaseModel):
    total_normalized_facts: int
    facts_with_open_flags:  int


class ReviewStats(BaseModel):
    human_corrections_count:        int   # raw correction events
    distinct_corrected_facts_count: int   # used in automation formula
    human_accepts_count:            int
    human_rejects_count:            int
    total_reviewed_facts:           int
    total_active_facts:             int
    unreviewed_facts:               int
    review_coverage_pct:            float


class AutomationStats(BaseModel):
    automation_pct:          Optional[float]  # None when no facts exist yet
    formula:                 str
    numerator:               Optional[int]    # None when no facts exist yet
    denominator:             Optional[int]    # None when no facts exist yet
    automation_pct_caveat:   str
    review_coverage_pct:     float


class PerformanceStats(BaseModel):
    avg_document_ingestion_time_seconds:  Optional[float]  # full end-to-end; null before Phase 4 migration
    avg_phase2_processing_time_seconds:   Optional[float]  # Phase 2 only; complementary metric
    avg_report_generation_time_seconds:   Optional[float]
    note_on_nulls:                        str


class DashboardStatsResponse(BaseModel):
    computed_at:    datetime
    pipeline:       PipelineStats
    extraction:     ExtractionStats
    trust:          TrustStats
    normalization:  NormalizationStats
    review:         ReviewStats
    automation:     AutomationStats
    performance:    PerformanceStats
