"""Phase 4: generated_reports, topic_clusters, document_topic_assignments, audit_log.

Also adds ingestion_started_at / ingestion_completed_at to documents table
so the Data Quality Dashboard can compute avg processing time per document.

Revision ID: 0004_phase4_schema
Revises: 033193bbf483
Create Date: 2026-09-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_phase4_schema"
down_revision = "033193bbf483"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # generated_reports
    # ------------------------------------------------------------------
    op.create_table(
        "generated_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("content_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("generation_time_seconds", sa.Double(), nullable=True),
        sa.Column("model_used", sa.String(200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # topic_clusters
    # ------------------------------------------------------------------
    op.create_table(
        "topic_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.String(30), nullable=False),
        sa.Column("cluster_params", postgresql.JSONB(), nullable=False),
        sa.Column("top_keywords", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_noise_cluster", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # document_topic_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "document_topic_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "topic_cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("topic_clusters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("similarity_score", sa.Double(), nullable=False),
        sa.Column("is_dominant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_dta_document_id", "document_topic_assignments", ["document_id"]
    )
    op.create_index(
        "ix_dta_topic_cluster_id", "document_topic_assignments", ["topic_cluster_id"]
    )

    # ------------------------------------------------------------------
    # audit_log
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewer", sa.String(100), nullable=False, server_default="anonymous"),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("target_table", sa.String(100), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_value", postgresql.JSONB(), nullable=True),
        sa.Column("after_value", postgresql.JSONB(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_log_target_id", "audit_log", ["target_id"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_action_type", "audit_log", ["action_type"])

    # ------------------------------------------------------------------
    # Add ingestion timing columns to documents
    # Used by dashboard to compute avg document processing time.
    # NULL for documents ingested before this migration (acceptable — see dashboard nullability rules).
    # ------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column("ingestion_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("ingestion_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "ingestion_completed_at")
    op.drop_column("documents", "ingestion_started_at")
    op.drop_index("ix_audit_log_action_type", table_name="audit_log")
    op.drop_index("ix_audit_log_timestamp", table_name="audit_log")
    op.drop_index("ix_audit_log_target_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_dta_topic_cluster_id", table_name="document_topic_assignments")
    op.drop_index("ix_dta_document_id", table_name="document_topic_assignments")
    op.drop_table("document_topic_assignments")
    op.drop_table("topic_clusters")
    op.drop_table("generated_reports")
