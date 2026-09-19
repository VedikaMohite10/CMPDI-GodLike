"""Abstract extractor interface + shared data-transfer objects.

Every extractor (pdf_digital, pdf_scanned, docx, spreadsheet, image)
returns an ExtractionResult which the orchestrator persists to Postgres.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextBlock:
    """One extracted text block (pre-persistence)."""
    page_number: int
    block_index: int
    block_type: str                     # 'paragraph' | 'heading' | 'list_item' | 'raw_ocr' | etc.
    text: str
    position: Optional[Dict[str, Any]] = None


@dataclass
class Table:
    """One extracted table (pre-persistence)."""
    page_number: int
    table_index: int
    raw_structure: Dict[str, Any]       # {headers, rows, shape}
    position: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None


@dataclass
class ImageAsset:
    """One extracted embedded image (pre-persistence).

    `data` holds the raw image bytes; the orchestrator writes these to storage.
    """
    page_number: int
    image_index: int
    data: bytes
    format: str                         # 'PNG' | 'JPEG' | etc.
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    position: Optional[Dict[str, Any]] = None


@dataclass
class ExtractionResult:
    """Complete extraction output from one document."""
    page_count: int
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    images: List[ImageAsset] = field(default_factory=list)
    # Per-page dimensions (for PDFs) — {page_number: (width_pts, height_pts)}
    page_dimensions: Dict[int, tuple] = field(default_factory=dict)


class AbstractExtractor(ABC):
    """Interface that all format-specific extractors must implement."""

    @abstractmethod
    async def extract(self, file_bytes: bytes) -> ExtractionResult:
        """Extract text, tables, and images from *file_bytes*.

        Must be idempotent and must not modify the input bytes.
        """
