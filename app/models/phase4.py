"""SQLAlchemy ORM models for Phase 4 tables.

Four tables:
  generated_reports          — one row per generated report (content stored as JSONB snapshot)
  topic_clusters             — one row per discovered cluster from the topic service
  document_topic_assignments — many-to-many: document ↔ topic cluster
  audit_log                  — immutable append-only record of every human review action
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Double, ForeignKey, Integer,
    String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GeneratedReport(Base):
    """Persisted record of a generated report.

    The full structured content (ReportContent dataclass serialised to dict) is
    stored in ``content_snapshot`` so:
      - exports can be re-generated without re-calling the LLM
      - the exact content that was exported can be audited later
    """
    __tablename__ = "generated_reports"

    id:                      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope:                   Mapped[dict]            = mapped_column(JSONB, nullable=False)
    status:                  Mapped[str]             = mapped_column(String(20), nullable=False, default="pending")
    content_snapshot:        Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    generation_time_seconds: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    model_used:              Mapped[Optional[str]]   = mapped_column(String(200), nullable=True)
    error:                   Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    created_at:              Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:              Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<GeneratedReport id={self.id} status={self.status!r}>"


class TopicCluster(Base):
    """One discovered topic cluster from the topic service."""
    __tablename__ = "topic_clusters"

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label:            Mapped[str]             = mapped_column(Text, nullable=False)
    algorithm:        Mapped[str]             = mapped_column(String(30), nullable=False)
    cluster_params:   Mapped[dict]            = mapped_column(JSONB, nullable=False)
    top_keywords:     Mapped[list]            = mapped_column(JSONB, nullable=False, default=list)
    document_count:   Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    is_noise_cluster: Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    is_active:        Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)
    computed_at:      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["DocumentTopicAssignment"]] = relationship(
        "DocumentTopicAssignment", back_populates="topic_cluster", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TopicCluster id={self.id} label={self.label!r} docs={self.document_count}>"


class DocumentTopicAssignment(Base):
    """Many-to-many: document -> topic cluster."""
    __tablename__ = "document_topic_assignments"

    id:               Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topic_clusters.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score: Mapped[float]     = mapped_column(Double, nullable=False)
    is_dominant:      Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    assigned_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic_cluster: Mapped["TopicCluster"] = relationship("TopicCluster", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<DocTopicAssignment doc={self.document_id} topic={self.topic_cluster_id} dominant={self.is_dominant}>"


class AuditLog(Base):
    """Immutable append-only record of every human review action.

    action_type values:
        'accept'           -- flag accepted; underlying value unchanged
        'correct'          -- human correction applied to normalized_fact
        'reject'           -- fact marked invalid (soft-deleted from active use)
        'resolve_conflict' -- human decision recorded on a conflict
    """
    __tablename__ = "audit_log"

    id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewer:     Mapped[str]            = mapped_column(String(100), nullable=False, default="anonymous")
    action_type:  Mapped[str]            = mapped_column(String(30), nullable=False)
    target_table: Mapped[str]            = mapped_column(String(100), nullable=False)
    target_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    before_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_value:  Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    note:         Mapped[Optional[str]]  = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action_type!r} target={self.target_id}>"
