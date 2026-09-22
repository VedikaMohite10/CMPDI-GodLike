"""Package init for extraction services."""
from app.services.extraction.base import (
    AbstractExtractor,
    ExtractionResult,
    ImageAsset,
    Table,
    TextBlock,
)
from app.services.extraction.pdf_digital import DigitalPDFExtractor
from app.services.extraction.pdf_scanned import ScannedPDFExtractor
from app.services.extraction.docx_extractor import DocxExtractor
from app.services.extraction.spreadsheet import SpreadsheetExtractor
from app.services.extraction.image_extractor import ImageExtractor

__all__ = [
    "AbstractExtractor",
    "ExtractionResult",
    "ImageAsset",
    "Table",
    "TextBlock",
    "DigitalPDFExtractor",
    "ScannedPDFExtractor",
    "DocxExtractor",
    "SpreadsheetExtractor",
    "ImageExtractor",
]
