"""Initial schema — all Phase 1 tables.

Revision ID: 0001
Revises:
Create Date: 2026-09-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("report_date", sa.Date, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("storage_path", sa.Text, nullable=False, unique=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("mime_type", sa.String(200), nullable=True),
        sa.Column("ocr_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="'pending'"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_documents_status", "documents", ["processing_status"])
    op.create_index("idx_documents_type", "documents", ["file_type"])
    op.create_index("idx_documents_upload", "documents", [sa.text("upload_date DESC")])

    # ------------------------------------------------------------------
    # pages
    # ------------------------------------------------------------------
    op.create_table(
        "pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("width_pts", sa.Float, nullable=True),
        sa.Column("height_pts", sa.Float, nullable=True),
        sa.UniqueConstraint("document_id", "page_number", name="uq_pages_doc_pagenum"),
    )
    op.create_index("idx_pages_document", "pages", ["document_id"])

    # ------------------------------------------------------------------
    # extracted_text_blocks
    # ------------------------------------------------------------------
    op.create_table(
        "extracted_text_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_index", sa.Integer, nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False, server_default="'paragraph'"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("position", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_text_blocks_document", "extracted_text_blocks", ["document_id"])
    op.create_index("idx_text_blocks_page", "extracted_text_blocks", ["page_id"])

    # ------------------------------------------------------------------
    # extracted_tables
    # ------------------------------------------------------------------
    op.create_table(
        "extracted_tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("table_index", sa.Integer, nullable=False),
        sa.Column("raw_structure", JSONB, nullable=False),
        sa.Column("position", JSONB, nullable=True),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_tables_document", "extracted_tables", ["document_id"])
    op.create_index("idx_tables_page", "extracted_tables", ["page_id"])

    # ------------------------------------------------------------------
    # extracted_images
    # ------------------------------------------------------------------
    op.create_table(
        "extracted_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_index", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("width_px", sa.Integer, nullable=True),
        sa.Column("height_px", sa.Integer, nullable=True),
        sa.Column("format", sa.String(20), nullable=True),
        sa.Column("position", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_images_document", "extracted_images", ["document_id"])
    op.create_index("idx_images_page", "extracted_images", ["page_id"])

    # ------------------------------------------------------------------
    # vector_index_log — bridges Qdrant point IDs → PostgreSQL record IDs
    # This is the critical link for retrieval contract point #1
    # ------------------------------------------------------------------
    op.create_table(
        "vector_index_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_id", UUID(as_uuid=True), sa.ForeignKey("extracted_text_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qdrant_point_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_vector_log_document", "vector_index_log", ["document_id"])
    op.create_index("idx_vector_log_block", "vector_index_log", ["block_id"])
    op.create_index("idx_vector_log_qdrant", "vector_index_log", ["qdrant_point_id"])


def downgrade() -> None:
    op.drop_table("vector_index_log")
    op.drop_table("extracted_images")
    op.drop_table("extracted_tables")
    op.drop_table("extracted_text_blocks")
    op.drop_table("pages")
    op.drop_table("documents")
