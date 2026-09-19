"""Abstract OCR engine interface.

Both Tesseract and VLM engines implement this interface so the
pdf_scanned extractor can switch between them via config without
knowing which backend is in use.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL.Image import Image as PILImage


@dataclass
class OCRResult:
    """Output of a single-page OCR run."""
    text: str                       # extracted text (may be empty)
    confidence: float               # 0–100; Tesseract page-level avg; 80.0 default for VLM
    engine: str                     # 'tesseract' | 'vlm'
    error: Optional[str] = None     # non-None means OCR failed gracefully


class AbstractOCREngine(ABC):
    """Interface for OCR engines. Implementations must be thread-safe."""

    @abstractmethod
    async def run(self, image: PILImage) -> OCRResult:
        """Run OCR on a single PIL image and return the result."""
