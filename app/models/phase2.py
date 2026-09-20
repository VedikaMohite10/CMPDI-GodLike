"""SQLAlchemy ORM models for Phase 2 tables."""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Double, Float,
    ForeignKey, Integer, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"

    id:             Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str]              = mapped_column(Text, nullable=False)
    entity_type:    Mapped[str]              = mapped_column(String(50), nullable=False)
    description:    Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:     Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aliases:         Mapped[list["EntityAlias"]]    = relationship("EntityAlias", back_populates="entity", cascade="all, delete-orphan")
    normalized_facts: Mapped[list["NormalizedFact"]] = relationship("NormalizedFact", back_populates="canonical_entity")

    __table_args__ = (
        UniqueConstraint("canonical_name", "entity_type", name="uq_entity_name_type"),
    )


class EntityAlias(Base):
    __tablename__ = "entity_aliases"

    id:                  Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_entity_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False)
    alias_text:          Mapped[str]        = mapped_column(Text, nullable=False, unique=True)
    resolution_method:   Mapped[str]        = mapped_column(String(30), nullable=False)
    confidence:          Mapped[float]      = mapped_column(Double, nullable=False)
    created_at:          Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    entity: Mapped["CanonicalEntity"] = relationship("CanonicalEntity", back_populates="aliases")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id:                    Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    table_id:              Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_tables.id", ondelete="SET NULL"), nullable=True)
    block_id:              Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_text_blocks.id", ondelete="SET NULL"), nullable=True)
    raw_entity_text:       Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    raw_metric_text:       Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    raw_value:             Mapped[str]             = mapped_column(Text, nullable=False)
    raw_unit_text:         Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    raw_date_text:         Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    extraction_method:     Mapped[str]             = mapped_column(String(30), nullable=False)
    extraction_model:      Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    llm_raw_output:        Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    is_obsolete:           Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    created_at:            Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    normalized_fact: Mapped[Optional["NormalizedFact"]] = relationship("NormalizedFact", back_populates="extracted_fact", uselist=False)


class NormalizedFact(Base):
    __tablename__ = "normalized_facts"

    id:                              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracted_fact_id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_facts.id", ondelete="CASCADE"), nullable=False, unique=True)
    canonical_entity_id:             Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_entities.id", ondelete="SET NULL"), nullable=True)
    entity_resolution_method:        Mapped[Optional[str]]   = mapped_column(String(30), nullable=True)
    entity_resolution_confidence:    Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    metric:                          Mapped[Optional[str]]   = mapped_column(String(200), nullable=True)
    metric_category:                 Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    normalized_value:                Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    normalized_unit:                 Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    original_value_text:             Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    original_unit_text:              Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    period_start:                    Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    period_end:                      Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    period_label:                    Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    date_parse_method:               Mapped[Optional[str]]   = mapped_column(String(30), nullable=True)
    normalization_notes:             Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    fact_processing_status:          Mapped[str]             = mapped_column(String(30), nullable=False, default="normalized")
    created_at:                      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:                      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    extracted_fact:    Mapped["ExtractedFact"]           = relationship("ExtractedFact", back_populates="normalized_fact")
    canonical_entity:  Mapped[Optional["CanonicalEntity"]] = relationship("CanonicalEntity", back_populates="normalized_facts")
    flags:             Mapped[list["ValidationFlag"]]    = relationship("ValidationFlag", back_populates="normalized_fact", cascade="all, delete-orphan")


class ValidationFlag(Base):
    __tablename__ = "validation_flags"

    id:                 Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False)
    flag_type:          Mapped[str]       = mapped_column(String(50), nullable=False)
    severity:           Mapped[str]       = mapped_column(String(20), nullable=False)
    detail:             Mapped[dict]      = mapped_column(JSONB, nullable=False)
    status:             Mapped[str]       = mapped_column(String(20), nullable=False, default="open")
    detected_at:        Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    normalized_fact: Mapped["NormalizedFact"] = relationship("NormalizedFact", back_populates="flags")


class Conflict(Base):
    __tablename__ = "conflicts"

    id:                  Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_entity_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False)
    metric:              Mapped[str]             = mapped_column(String(200), nullable=False)
    period_start:        Mapped[date]            = mapped_column(Date, nullable=False)
    period_end:          Mapped[date]            = mapped_column(Date, nullable=False)
    fact_a_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False)
    fact_b_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False)
    value_a:             Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    value_b:             Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    unit_a:              Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    unit_b:              Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    delta_pct:           Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    status:              Mapped[str]             = mapped_column(String(20), nullable=False, default="open")
    detected_at:         Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("fact_a_id", "fact_b_id", name="uq_conflict_pair"),
        CheckConstraint("fact_a_id <> fact_b_id", name="chk_facts_distinct"),
    )

    entity: Mapped["CanonicalEntity"] = relationship("CanonicalEntity")


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope:            Mapped[str]             = mapped_column(String(20), nullable=False)
    document_id_a:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    document_id_b:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    fact_id_a:        Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=True)
    fact_id_b:        Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=True)
    similarity_score: Mapped[float]           = mapped_column(Double, nullable=False)
    detection_method: Mapped[str]             = mapped_column(String(30), nullable=False)
    status:           Mapped[str]             = mapped_column(String(20), nullable=False, default="open")
    detected_at:      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactProcessingLog(Base):
    __tablename__ = "fact_processing_log"

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    phase:            Mapped[str]             = mapped_column(String(30), nullable=False, default="phase2")
    status:           Mapped[str]             = mapped_column(String(30), nullable=False)
    facts_extracted:  Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    facts_normalized: Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    facts_flagged:    Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    conflicts_found:  Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    error:            Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    started_at:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("document_id", "phase", name="uq_doc_phase"),
    )
