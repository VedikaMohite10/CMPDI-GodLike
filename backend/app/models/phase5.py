"""SQLAlchemy ORM models for Phase 5 tables.

Six new tables:
  users                  — authentication (username, bcrypt password, role)
  parliamentary_queries  — parliamentary copilot with strict status FSM
                           draft → pending_review → approved | rejected
                           NEVER auto-finalized
  region_mapping         — links canonical_entities to geographic regions
  forecast_results       — stores every forecast; always labeled "Model-based forecast"
  benchmark_runs         — timestamped accuracy snapshots from the harness
  benchmark_ground_truth — labeled datasets (real and synthetic) for the harness
"""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float,
    ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    """Application user for JWT-based authentication.

    Roles:
      analyst  — read + query + ingest + report generation
      reviewer — analyst permissions + review/approval actions
      admin    — all permissions + user management
    """
    __tablename__ = "users"

    id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username:        Mapped[str]            = mapped_column(String(150), nullable=False, unique=True)
    hashed_password: Mapped[str]            = mapped_column(Text, nullable=False)
    role:            Mapped[str]            = mapped_column(String(20), nullable=False, default="analyst")
    is_active:       Mapped[bool]           = mapped_column(Boolean, nullable=False, default=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('analyst', 'reviewer', 'admin')", name="chk_user_role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"


# ---------------------------------------------------------------------------
# ParliamentaryQuery
# ---------------------------------------------------------------------------

class ParliamentaryQuery(Base):
    """Parliamentary Query Copilot record.

    Status finite-state machine:
      draft          — internal state during generation (rarely persisted at this stage)
      pending_review — stored immediately after generation; NEVER auto-advanced
      approved       — reviewer explicitly approved; final_answer exposed
      rejected       — reviewer rejected; draft_answer suppressed

    Design guarantee: final_answer is ONLY returned to callers when
    status == 'approved'. Any response package that calls GET /parliamentary/{id}
    while status != 'approved' receives final_answer=null.
    """
    __tablename__ = "parliamentary_queries"

    id:                  Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question:            Mapped[str]             = mapped_column(Text, nullable=False)
    submitted_by_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Pipeline artifacts (same structure as QueryResponse from Phase 3)
    intent_plan:         Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    evidence:            Mapped[list]            = mapped_column(JSONB, nullable=False, default=list)
    conflicts_surfaced:  Mapped[list]            = mapped_column(JSONB, nullable=False, default=list)
    analytics_results:   Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    calculation:         Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    confidence:          Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    reasoning_type:      Mapped[Optional[str]]   = mapped_column(String(30), nullable=True)
    has_open_conflicts:  Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)

    # The draft answer — visible to reviewers in pending_review state, but
    # NEVER returned via the public "final answer" endpoint until approved.
    draft_answer:        Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    # Status FSM
    status:              Mapped[str]             = mapped_column(String(20), nullable=False, default="pending_review")

    # Reviewer action
    reviewer_id:         Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_note:       Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    reviewed_at:         Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Model attribution
    model_used_intent:   Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    model_used_synthesis: Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)

    created_at:          Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:          Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected')",
            name="chk_parl_status",
        ),
    )

    submitted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[submitted_by_id])
    reviewer:     Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self) -> str:
        return f"<ParliamentaryQuery id={self.id} status={self.status!r}>"


# ---------------------------------------------------------------------------
# RegionMapping
# ---------------------------------------------------------------------------

class RegionMapping(Base):
    """Geographic mapping: canonical_entity -> region/state.

    source values:
      reference_table  — manually curated from known subsidiary/coalfield geography
      document_derived — extracted from document text (supplementary; never overwrites
                         reference_table rows)

    The source column is returned in every API response so consumers can
    distinguish authoritative mappings from document-derived ones.
    """
    __tablename__ = "region_mapping"

    id:                  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_entity_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False)
    region_id:           Mapped[str]            = mapped_column(String(10), nullable=False)   # e.g. "JH", "WB", "PAN"
    region_name:         Mapped[str]            = mapped_column(String(100), nullable=False)
    state_name:          Mapped[str]            = mapped_column(String(100), nullable=False)
    source:              Mapped[str]            = mapped_column(String(20), nullable=False, default="reference_table")
    source_note:         Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    created_at:          Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("canonical_entity_id", name="uq_region_entity"),
        CheckConstraint("source IN ('reference_table', 'document_derived')", name="chk_region_source"),
    )

    def __repr__(self) -> str:
        return f"<RegionMapping entity={self.canonical_entity_id} region={self.region_id!r}>"


# ---------------------------------------------------------------------------
# ForecastResult
# ---------------------------------------------------------------------------

class ForecastResult(Base):
    """Stored output of the forecasting engine.

    The forecast_type column is ALWAYS set to 'Model-based forecast'.
    This is enforced at the ORM level so no consumer can accidentally
    present a forecast as an official projection.
    """
    __tablename__ = "forecast_results"

    id:                   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False)
    metric:               Mapped[str]             = mapped_column(String(200), nullable=False)
    horizon_years:        Mapped[int]             = mapped_column(Integer, nullable=False)
    model_used:           Mapped[str]             = mapped_column(String(50), nullable=False)   # "moving_average" | "exponential_smoothing" | "arima"
    escalation_reason:    Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    training_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    training_period_end:   Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    training_data_points: Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    forecast_data:        Mapped[dict]            = mapped_column(JSONB, nullable=False, default=dict)
    # forecast_data structure:
    # {
    #   "years": [...],
    #   "predicted_values": [...],
    #   "lower_bound": [...],
    #   "upper_bound": [...],
    #   "unit": "...",
    #   "assumptions": [...],
    # }
    data_quality_summary: Mapped[dict]            = mapped_column(JSONB, nullable=False, default=dict)
    # data_quality_summary structure:
    # {
    #   "available_points": N,
    #   "missing_period_ratio": 0.xx,
    #   "open_conflicts": N,
    #   "avg_extraction_confidence": 0.xx,
    # }

    # ALWAYS "Model-based forecast" — enforced by the service layer and stored
    # here so every consumer of this table sees the label even without the API.
    forecast_type:        Mapped[str]             = mapped_column(String(50), nullable=False, default="Model-based forecast")

    # Insufficient data case — forecast_data and model_used are empty/null when True
    insufficient_data:    Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    insufficient_reason:  Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    created_at:           Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "forecast_type = 'Model-based forecast'",
            name="chk_forecast_type_label",
        ),
    )

    def __repr__(self) -> str:
        return f"<ForecastResult id={self.id} entity={self.entity_id} metric={self.metric!r} model={self.model_used!r}>"


# ---------------------------------------------------------------------------
# BenchmarkRun
# ---------------------------------------------------------------------------

class BenchmarkRun(Base):
    """Timestamped result of a benchmark harness run.

    is_latest tracks which run is the current one — only one row at a time
    should have is_latest=True. The harness resets all rows to False before
    inserting the new one.

    results JSONB structure:
    {
      "real": {                   -- metrics from real documents
        "text_extraction_accuracy": 0.xx,
        "table_extraction_accuracy": 0.xx,
        "entity_resolution_accuracy": 0.xx,
        "unit_normalization_accuracy": 0.xx,
        "conflict_detection_precision": 0.xx,
        "conflict_detection_recall": 0.xx,
        "citation_accuracy": 0.xx,
        "query_answer_correctness": 0.xx,
        "sample_size": N,
      },
      "synthetic": {              -- metrics from synthetic stress-test docs
        ...same keys...,
        "synthetic_types_tested": [...],
      },
    }
    NOTE: real and synthetic metrics are NEVER aggregated into a single number.
    """
    __tablename__ = "benchmark_runs"

    id:                       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_at:                   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    results:                  Mapped[dict]      = mapped_column(JSONB, nullable=False, default=dict)
    document_count_real:      Mapped[int]       = mapped_column(Integer, nullable=False, default=0)
    document_count_synthetic: Mapped[int]       = mapped_column(Integer, nullable=False, default=0)
    sample_size:              Mapped[int]       = mapped_column(Integer, nullable=False, default=0)
    is_latest:                Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    run_note:                 Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<BenchmarkRun id={self.id} run_at={self.run_at} is_latest={self.is_latest}>"


# ---------------------------------------------------------------------------
# BenchmarkGroundTruth
# ---------------------------------------------------------------------------

class BenchmarkGroundTruth(Base):
    """Static ground-truth label sets used by the benchmark harness.

    is_synthetic MUST be True for any row whose labels come from a
    deliberately constructed stress-test document. This field is enforced
    at insert time by the harness loader and stored permanently so no
    benchmark result can ever be mistakenly attributed to real CMPDI data.

    labels JSONB structure (per label set):
    [
      {
        "fact_id": "...",           -- optional: links to a DB fact
        "entity":  "...",           -- canonical entity name expected
        "metric":  "...",
        "expected_value": N,
        "expected_unit":  "...",
        "expected_period": "...",
        "expected_conflict": true|false,   -- for conflict injection docs
        "source_text_excerpt": "...",
      },
      ...
    ]
    """
    __tablename__ = "benchmark_ground_truth"

    id:             Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    label_set_name: Mapped[str]             = mapped_column(String(200), nullable=False, unique=True)
    labels:         Mapped[list]            = mapped_column(JSONB, nullable=False, default=list)
    is_synthetic:   Mapped[bool]            = mapped_column(Boolean, nullable=False)
    synthetic_type: Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    created_at:     Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "(is_synthetic = false AND synthetic_type IS NULL) OR (is_synthetic = true AND synthetic_type IS NOT NULL)",
            name="chk_synthetic_type_consistency",
        ),
    )

    def __repr__(self) -> str:
        return f"<BenchmarkGroundTruth name={self.label_set_name!r} synthetic={self.is_synthetic}>"
