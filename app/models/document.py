"""SQLAlchemy ORM models — `documents` table."""
import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Boolean, Integer, BigInteger, DateTime, Date, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Permanent storage path within the storage root — never updated after creation.
    # This satisfies retrieval contract points #3 and #5.
    storage_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ocr_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", server_default="'pending'"
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Ingestion timing — written by the ingestion pipeline so the dashboard
    # can compute avg document processing time (Phase 4). NULL for documents
    # ingested before migration 0004 (acceptable; dashboard returns null with a note).
    ingestion_started_at:   Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ingestion_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    pages: Mapped[List["Page"]] = relationship(  # noqa: F821
        "Page", back_populates="document", cascade="all, delete-orphan", lazy="select"
    )
    text_blocks: Mapped[List["ExtractedTextBlock"]] = relationship(  # noqa: F821
        "ExtractedTextBlock", back_populates="document", cascade="all, delete-orphan"
    )
    tables: Mapped[List["ExtractedTable"]] = relationship(  # noqa: F821
        "ExtractedTable", back_populates="document", cascade="all, delete-orphan"
    )
    images: Mapped[List["ExtractedImage"]] = relationship(  # noqa: F821
        "ExtractedImage", back_populates="document", cascade="all, delete-orphan"
    )
    vector_logs: Mapped[List["VectorIndexLog"]] = relationship(  # noqa: F821
        "VectorIndexLog", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.processing_status!r}>"
