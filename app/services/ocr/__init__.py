"""Package init for OCR services."""
from app.services.ocr.base import AbstractOCREngine, OCRResult
from app.services.ocr.tesseract_engine import TesseractEngine
from app.services.ocr.vlm_engine import VLMEngine

__all__ = ["AbstractOCREngine", "OCRResult", "TesseractEngine", "VLMEngine"]
