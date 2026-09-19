"""Tesseract OCR engine implementation.

Uses pytesseract (a thin wrapper around the Tesseract CLI) to extract text
from PIL images. All CPU-bound work is offloaded to a thread via asyncio.to_thread.
"""
import asyncio
import logging
from typing import Optional

import pytesseract
from PIL.Image import Image as PILImage

from app.services.ocr.base import AbstractOCREngine, OCRResult

logger = logging.getLogger(__name__)


def _tesseract_sync(image: PILImage) -> tuple[str, float]:
    """Blocking Tesseract call — runs in a thread pool."""
    try:
        # image_to_data gives per-word confidence scores
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            output_type=pytesseract.Output.DICT,
        )
        # Compute page-level average confidence (ignoring -1 sentinel values)
        confidences = [c for c in data["conf"] if isinstance(c, (int, float)) and c >= 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip(), avg_confidence
    except Exception as exc:
        logger.warning("Tesseract failed: %s", exc)
        return "", 0.0


class TesseractEngine(AbstractOCREngine):
    """Tesseract OCR — fast, CPU-friendly, suitable for clean scans."""

    async def run(self, image: PILImage) -> OCRResult:
        text, confidence = await asyncio.to_thread(_tesseract_sync, image)
        if not text:
            return OCRResult(
                text="",
                confidence=confidence,
                engine="tesseract",
                error="Tesseract returned empty output.",
            )
        return OCRResult(text=text, confidence=confidence, engine="tesseract")
