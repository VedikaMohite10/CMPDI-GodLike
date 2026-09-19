"""SQLAlchemy ORM models — extraction tables.

Three models, all requiring non-null document_id + page_id
to satisfy provenance requirement (retrieval contract point #2).
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ExtractedTextBlock(Base):
    """One contiguous text block from any source format.

    block_type values:
      'paragraph' | 'heading' | 'list_item' | 'caption' | 'header_footer' | 'raw_ocr'

    position JSONB shape:
      PDF  → {"x0": f, "y0": f, "x1": f, "y1": f}   (bounding box in pts)
      DOCX → {"paragraph_index": n}
      XLSX → {"sheet": "SheetName", "row": r, "col": c}
    """
    __tablename__ = "extracted_text_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Provenance — both must be non-null (retrieval contract point #2)
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
        index=True,
    )
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="paragraph", server_default="'paragraph'"
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="text_blocks")  # noqa: F821
    page: Mapped["Page"] = relationship("Page", back_populates="text_blocks")  # noqa: F821
    vector_log: Mapped[Optional["VectorIndexLog"]] = relationship(  # noqa: F821
        "VectorIndexLog", back_populates="block", uselist=False
    )

    def __repr__(self) -> str:
        return f"<TextBlock id={self.id} type={self.block_type!r} chars={len(self.text)}>"


class ExtractedTable(Base):
    """One detected table, stored as structured JSON.

    raw_structure shape:
      {
        "headers": ["col1", "col2", ...],
        "rows":    [["val", "val", ...], ...],
        "shape":   [n_rows, n_cols]
      }
    """
    __tablename__ = "extracted_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
        index=True,
    )
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_structure: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    position: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="tables")  # noqa: F821
    page: Mapped["Page"] = relationship("Page", back_populates="tables")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Table id={self.id} index={self.table_index}>"


class ExtractedImage(Base):
    """One embedded image / chart extracted from a source document.

    storage_path is relative to STORAGE_ROOT (under images/ subdirectory).
    The original document's file is untouched; this is a separately stored derivative.
    """
    __tablename__ = "extracted_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
        index=True,
    )
    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    width_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    position: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="images")  # noqa: F821
    page: Mapped["Page"] = relationship("Page", back_populates="images")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Image id={self.id} index={self.image_index} fmt={self.format!r}>"
