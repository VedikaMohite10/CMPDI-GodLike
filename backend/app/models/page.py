"""SQLAlchemy ORM models — `pages` table."""
import uuid
from typing import Optional, List

from sqlalchemy import Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_pages_doc_pagenum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # PDF page dimensions in points (72 pts = 1 inch). NULL for non-PDF formats.
    width_pts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_pts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="pages"
    )
    text_blocks: Mapped[List["ExtractedTextBlock"]] = relationship(  # noqa: F821
        "ExtractedTextBlock", back_populates="page", cascade="all, delete-orphan"
    )
    tables: Mapped[List["ExtractedTable"]] = relationship(  # noqa: F821
        "ExtractedTable", back_populates="page", cascade="all, delete-orphan"
    )
    images: Mapped[List["ExtractedImage"]] = relationship(  # noqa: F821
        "ExtractedImage", back_populates="page", cascade="all, delete-orphan"
    )
    vector_logs: Mapped[List["VectorIndexLog"]] = relationship(  # noqa: F821
        "VectorIndexLog", back_populates="page", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Page doc={self.document_id} page={self.page_number}>"
