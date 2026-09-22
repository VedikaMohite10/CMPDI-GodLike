"""SQLAlchemy ORM model — `vector_index_log` table.

This table is the critical bridge between Qdrant and PostgreSQL.
Every Qdrant point has a corresponding row here so that a retrieval
layer can follow:
  Qdrant point_id → vector_index_log.qdrant_point_id
                  → block_id, page_id, document_id
                  → extracted_text_blocks, pages, documents
                  → documents.storage_path → original file

This satisfies retrieval contract point #1.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class VectorIndexLog(Base):
    __tablename__ = "vector_index_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # All three IDs are required — they form the Qdrant → Postgres provenance chain
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_text_blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The Qdrant point ID that holds the vector — must be unique across the collection
    qdrant_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    embedded_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="vector_logs")  # noqa: F821
    page: Mapped["Page"] = relationship("Page", back_populates="vector_logs")  # noqa: F821
    block: Mapped["ExtractedTextBlock"] = relationship(  # noqa: F821
        "ExtractedTextBlock", back_populates="vector_log"
    )

    def __repr__(self) -> str:
        return f"<VectorIndexLog block={self.block_id} qdrant={self.qdrant_point_id}>"
