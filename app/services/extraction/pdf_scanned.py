"""Extractor for scanned PDFs (and standalone images).

Pipeline:
  1. Render each PDF page to a PIL image using pdf2image (Poppler)
  2. Run the configured OCR engine (Tesseract / VLM / hybrid)
  3. Wrap each page's OCR output in a single TextBlock (type='raw_ocr')

In hybrid mode:
  Run Tesseract first; if page confidence < TESSERACT_CONFIDENCE_THRESHOLD,
  fall back to VLM for that page only.
"""
import asyncio
import io
import logging
from typing import Dict, List

from PIL import Image as PILImage

from app.config import get_settings
from app.services.extraction.base import (
    AbstractExtractor,
    ExtractionResult,
    TextBlock,
)
from app.services.ocr.base import AbstractOCREngine, OCRResult
from app.services.ocr.tesseract_engine import TesseractEngine
from app.services.ocr.vlm_engine import VLMEngine

logger = logging.getLogger(__name__)
settings = get_settings()


def _render_pdf_pages_sync(file_bytes: bytes) -> List[PILImage.Image]:
    """Rasterize all PDF pages to PIL images using pdf2image (Poppler).

    DPI=200 is a good balance: readable for OCR, not enormous in memory.
    """
    from pdf2image import convert_from_bytes
    return convert_from_bytes(file_bytes, dpi=200)


def _get_ocr_engines() -> tuple[AbstractOCREngine, AbstractOCREngine | None]:
    """Return (primary_engine, fallback_engine) based on OCR_ENGINE config."""
    engine_cfg = settings.OCR_ENGINE.lower()
    tesseract = TesseractEngine()
    vlm = VLMEngine()

    if engine_cfg == "tesseract":
        return tesseract, None
    elif engine_cfg == "vlm":
        return vlm, None
    else:  # hybrid
        return tesseract, vlm


class ScannedPDFExtractor(AbstractExtractor):
    """OCR-based extractor for scanned PDFs.

    Each page becomes exactly one TextBlock of type 'raw_ocr'.
    No table reconstruction is attempted in this phase for scanned PDFs —
    the raw OCR text is embedded and searchable.
    """

    async def extract(self, file_bytes: bytes) -> ExtractionResult:
        # Step 1: Render pages (blocking — Poppler)
        logger.info("Rendering scanned PDF pages via pdf2image…")
        pages: List[PILImage.Image] = await asyncio.to_thread(
            _render_pdf_pages_sync, file_bytes
        )
        page_count = len(pages)
        logger.info("Rendered %d pages.", page_count)

        primary, fallback = _get_ocr_engines()
        text_blocks: List[TextBlock] = []
        page_dimensions: Dict[int, tuple] = {}

        for page_num, pil_img in enumerate(pages, start=1):
            w, h = pil_img.size
            page_dimensions[page_num] = (float(w), float(h))

            # Step 2: OCR
            result: OCRResult = await primary.run(pil_img)

            if (
                fallback is not None
                and result.confidence < settings.TESSERACT_CONFIDENCE_THRESHOLD
            ):
                logger.info(
                    "Page %d Tesseract confidence %.1f < threshold %.1f — falling back to VLM.",
                    page_num,
                    result.confidence,
                    settings.TESSERACT_CONFIDENCE_THRESHOLD,
                )
                vlm_result: OCRResult = await fallback.run(pil_img)
                if vlm_result.text:
                    result = vlm_result

            text = result.text or ""
            if text:
                text_blocks.append(
                    TextBlock(
                        page_number=page_num,
                        block_index=0,
                        block_type="raw_ocr",
                        text=text,
                        position={"x0": 0.0, "y0": 0.0, "x1": float(w), "y1": float(h)},
                    )
                )
            else:
                logger.warning("Page %d produced no OCR text (engine=%s).", page_num, result.engine)

        return ExtractionResult(
            page_count=page_count,
            text_blocks=text_blocks,
            tables=[],
            images=[],
            page_dimensions=page_dimensions,
        )
