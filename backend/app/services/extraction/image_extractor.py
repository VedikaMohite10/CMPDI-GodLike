"""Extractor for standalone image files (JPG, PNG, etc.).

Runs OCR on the image and wraps output in a single TextBlock.
One logical page (page_number=1).
"""
import asyncio
import io
import logging

from PIL import Image as PILImage

from app.config import get_settings
from app.services.extraction.base import (
    AbstractExtractor,
    ExtractionResult,
    TextBlock,
)
from app.services.ocr.base import OCRResult
from app.services.ocr.tesseract_engine import TesseractEngine
from app.services.ocr.vlm_engine import VLMEngine

logger = logging.getLogger(__name__)
settings = get_settings()


def _open_image_sync(file_bytes: bytes) -> PILImage.Image:
    return PILImage.open(io.BytesIO(file_bytes)).convert("RGB")


class ImageExtractor(AbstractExtractor):
    """OCR-based extractor for standalone JPG / PNG images."""

    async def extract(self, file_bytes: bytes) -> ExtractionResult:
        pil_img = await asyncio.to_thread(_open_image_sync, file_bytes)
        w, h = pil_img.size

        engine_cfg = settings.OCR_ENGINE.lower()

        if engine_cfg == "vlm":
            primary = VLMEngine()
            fallback = None
        else:
            primary = TesseractEngine()
            fallback = VLMEngine() if engine_cfg == "hybrid" else None

        result: OCRResult = await primary.run(pil_img)

        if (
            fallback is not None
            and result.confidence < settings.TESSERACT_CONFIDENCE_THRESHOLD
        ):
            logger.info(
                "Image OCR confidence %.1f < threshold — falling back to VLM.",
                result.confidence,
            )
            vlm_result = await fallback.run(pil_img)
            if vlm_result.text:
                result = vlm_result

        text_blocks = []
        if result.text:
            text_blocks.append(
                TextBlock(
                    page_number=1,
                    block_index=0,
                    block_type="raw_ocr",
                    text=result.text,
                    position={"x0": 0.0, "y0": 0.0, "x1": float(w), "y1": float(h)},
                )
            )

        return ExtractionResult(
            page_count=1,
            text_blocks=text_blocks,
            tables=[],
            images=[],
            page_dimensions={1: (float(w), float(h))},
        )
