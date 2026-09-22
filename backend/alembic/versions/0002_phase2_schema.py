"""Phase 2 schema — Data Trust Engine tables.

Revision ID: 0002
Revises:     0001
Create Date: 2026-09-20

Adds 7 new tables (never touches Phase 1 tables):
  canonical_entities, entity_aliases,
  extracted_facts, normalized_facts,
  validation_flags, conflicts,
  duplicate_candidates, fact_processing_log
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, DOUBLE_PRECISION
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # canonical_entities
    # ------------------------------------------------------------------
    op.create_table(
        "canonical_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("canonical_name", "entity_type", name="uq_entity_name_type"),
    )
    op.create_index("idx_entities_type", "canonical_entities", ["entity_type"])

    # ------------------------------------------------------------------
    # entity_aliases
    # ------------------------------------------------------------------
    op.create_table(
        "entity_aliases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_entity_id", UUID(as_uuid=True),
                  sa.ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.Text, nullable=False),
        sa.Column("resolution_method", sa.String(30), nullable=False),
        sa.Column("confidence", DOUBLE_PRECISION, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("alias_text", name="uq_alias_text"),
    )
    op.create_index("idx_aliases_entity", "entity_aliases", ["canonical_entity_id"])
    op.create_index("idx_aliases_text",   "entity_aliases", ["alias_text"])

    # ------------------------------------------------------------------
    # extracted_facts  — raw LLM + heuristic output, tied to Phase 1
    # ------------------------------------------------------------------
    op.create_table(
        "extracted_facts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True),
                  sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("table_id", UUID(as_uuid=True),
                  sa.ForeignKey("extracted_tables.id", ondelete="SET NULL"), nullable=True),
        sa.Column("block_id", UUID(as_uuid=True),
                  sa.ForeignKey("extracted_text_blocks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_entity_text",  sa.Text, nullable=True),
        sa.Column("raw_metric_text",  sa.Text, nullable=True),
        sa.Column("raw_value",        sa.Text, nullable=False),
        sa.Column("raw_unit_text",    sa.Text, nullable=True),
        sa.Column("raw_date_text",    sa.Text, nullable=True),
        sa.Column("extraction_method",   sa.String(30), nullable=False),
        sa.Column("extraction_model",    sa.String(100), nullable=True),
        sa.Column("llm_raw_output",      JSONB, nullable=True),
        sa.Column("extraction_confidence", DOUBLE_PRECISION, nullable=True),
        sa.Column("is_obsolete", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_efacts_document", "extracted_facts", ["document_id"])
    op.create_index("idx_efacts_page",     "extracted_facts", ["page_id"])
    op.create_index("idx_efacts_table",    "extracted_facts", ["table_id"],
                    postgresql_where=sa.text("table_id IS NOT NULL"))
    op.create_index("idx_efacts_block",    "extracted_facts", ["block_id"],
                    postgresql_where=sa.text("block_id IS NOT NULL"))
    op.create_index("idx_efacts_obsolete", "extracted_facts", ["is_obsolete"])

    # ------------------------------------------------------------------
    # normalized_facts — deterministic normalization of extracted_facts
    # ------------------------------------------------------------------
    op.create_table(
        "normalized_facts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("extracted_fact_id", UUID(as_uuid=True),
                  sa.ForeignKey("extracted_facts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("canonical_entity_id", UUID(as_uuid=True),
                  sa.ForeignKey("canonical_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_resolution_method",     sa.String(30), nullable=True),
        sa.Column("entity_resolution_confidence", DOUBLE_PRECISION, nullable=True),
        sa.Column("metric",           sa.String(200), nullable=True),
        sa.Column("metric_category",  sa.String(100), nullable=True),
        sa.Column("normalized_value", DOUBLE_PRECISION, nullable=True),
        sa.Column("normalized_unit",  sa.String(50), nullable=True),
        sa.Column("original_value_text", sa.Text, nullable=True),
        sa.Column("original_unit_text",  sa.Text, nullable=True),
        sa.Column("period_start",     sa.Date, nullable=True),
        sa.Column("period_end",       sa.Date, nullable=True),
        sa.Column("period_label",     sa.String(100), nullable=True),
        sa.Column("date_parse_method", sa.String(30), nullable=True),
        sa.Column("normalization_notes", JSONB, nullable=True),
        sa.Column("fact_processing_status", sa.String(30), nullable=False, server_default="'normalized'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_nfacts_entity",  "normalized_facts", ["canonical_entity_id"])
    op.create_index("idx_nfacts_metric",  "normalized_facts", ["metric"])
    op.create_index("idx_nfacts_period",  "normalized_facts", ["period_start", "period_end"])
    op.create_index("idx_nfacts_efact",   "normalized_facts", ["extracted_fact_id"])
    op.create_index("idx_nfacts_conflict_key", "normalized_facts",
                    ["canonical_entity_id", "metric", "period_start", "period_end"],
                    postgresql_where=sa.text(
                        "canonical_entity_id IS NOT NULL AND metric IS NOT NULL AND period_start IS NOT NULL"
                    ))

    # ------------------------------------------------------------------
    # validation_flags
    # ------------------------------------------------------------------
    op.create_table(
        "validation_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("normalized_fact_id", UUID(as_uuid=True),
                  sa.ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("flag_type", sa.String(50), nullable=False),
        sa.Column("severity",  sa.String(20), nullable=False),
        sa.Column("detail",    JSONB, nullable=False),
        sa.Column("status",    sa.String(20), nullable=False, server_default="'open'"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_vflags_fact",     "validation_flags", ["normalized_fact_id"])
    op.create_index("idx_vflags_type",     "validation_flags", ["flag_type"])
    op.create_index("idx_vflags_severity", "validation_flags", ["severity"])
    op.create_index("idx_vflags_status",   "validation_flags", ["status"])

    # ------------------------------------------------------------------
    # conflicts
    # ------------------------------------------------------------------
    op.create_table(
        "conflicts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_entity_id", UUID(as_uuid=True),
                  sa.ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric",       sa.String(200), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end",   sa.Date, nullable=False),
        sa.Column("fact_a_id", UUID(as_uuid=True),
                  sa.ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fact_b_id", UUID(as_uuid=True),
                  sa.ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value_a", DOUBLE_PRECISION, nullable=True),
        sa.Column("value_b", DOUBLE_PRECISION, nullable=True),
        sa.Column("unit_a",  sa.String(50), nullable=True),
        sa.Column("unit_b",  sa.String(50), nullable=True),
        sa.Column("delta_pct", DOUBLE_PRECISION, nullable=True),
        sa.Column("status",     sa.String(20), nullable=False, server_default="'open'"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("fact_a_id", "fact_b_id", name="uq_conflict_pair"),
        sa.CheckConstraint("fact_a_id <> fact_b_id", name="chk_facts_distinct"),
    )
    op.create_index("idx_conflicts_entity", "conflicts", ["canonical_entity_id"])
    op.create_index("idx_conflicts_metric", "conflicts", ["metric"])
    op.create_index("idx_conflicts_status", "conflicts", ["status"])
    op.create_index("idx_conflicts_fact_a", "conflicts", ["fact_a_id"])
    op.create_index("idx_conflicts_fact_b", "conflicts", ["fact_b_id"])

    # ------------------------------------------------------------------
    # duplicate_candidates
    # ------------------------------------------------------------------
    op.create_table(
        "duplicate_candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("document_id_a", UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("document_id_b", UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("fact_id_a", UUID(as_uuid=True),
                  sa.ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("fact_id_b", UUID(as_uuid=True),
                  sa.ForeignKey("normalized_facts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("similarity_score",  DOUBLE_PRECISION, nullable=False),
        sa.Column("detection_method",  sa.String(30), nullable=False),
        sa.Column("status",     sa.String(20), nullable=False, server_default="'open'"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "scope != 'document' OR (document_id_a IS NOT NULL AND document_id_b IS NOT NULL)",
            name="chk_scope_doc",
        ),
        sa.CheckConstraint(
            "scope != 'fact' OR (fact_id_a IS NOT NULL AND fact_id_b IS NOT NULL)",
            name="chk_scope_fact",
        ),
    )
    op.create_index("idx_dupes_doc_a",  "duplicate_candidates", ["document_id_a"],
                    postgresql_where=sa.text("document_id_a IS NOT NULL"))
    op.create_index("idx_dupes_doc_b",  "duplicate_candidates", ["document_id_b"],
                    postgresql_where=sa.text("document_id_b IS NOT NULL"))
    op.create_index("idx_dupes_status", "duplicate_candidates", ["status"])

    # ------------------------------------------------------------------
    # fact_processing_log — idempotency guard + job state per document
    # ------------------------------------------------------------------
    op.create_table(
        "fact_processing_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase",   sa.String(30), nullable=False, server_default="'phase2'"),
        sa.Column("status",  sa.String(30), nullable=False),
        sa.Column("facts_extracted",   sa.Integer, nullable=False, server_default="0"),
        sa.Column("facts_normalized",  sa.Integer, nullable=False, server_default="0"),
        sa.Column("facts_flagged",     sa.Integer, nullable=False, server_default="0"),
        sa.Column("conflicts_found",   sa.Integer, nullable=False, server_default="0"),
        sa.Column("error",        sa.Text, nullable=True),
        sa.Column("started_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("document_id", "phase", name="uq_doc_phase"),
    )
    op.create_index("idx_fpl_document", "fact_processing_log", ["document_id"])
    op.create_index("idx_fpl_status",   "fact_processing_log", ["status"])


def downgrade() -> None:
    op.drop_table("fact_processing_log")
    op.drop_table("duplicate_candidates")
    op.drop_table("conflicts")
    op.drop_table("validation_flags")
    op.drop_table("normalized_facts")
    op.drop_table("extracted_facts")
    op.drop_table("entity_aliases")
    op.drop_table("canonical_entities")
