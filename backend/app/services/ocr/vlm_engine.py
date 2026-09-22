"""VLM OCR engine — qwen2.5vl:3b via Ollama.

Converts a PIL image to base64, sends it to the Ollama chat API,
and returns the model's text as the OCR result.

Note: This engine is SLOW on CPU (30–120s per page).
Use only when Tesseract confidence is below threshold (hybrid mode)
or when OCR_ENGINE=vlm is explicitly configured.
"""
import base64
import io
import logging
from PIL.Image import Image as PILImage

from app.services.ocr.base import AbstractOCREngine, OCRResult
from app.services import ollama_client

logger = logging.getLogger(__name__)

# VLM output cannot give a per-word confidence; we assign a fixed proxy value
# so that the hybrid engine's threshold comparisons still work.
VLM_CONFIDENCE_PROXY = 80.0


def _image_to_b64(image: PILImage) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class VLMEngine(AbstractOCREngine):
    """qwen2.5vl:3b OCR engine via local Ollama API.

    More accurate than Tesseract on degraded scans and complex tables,
    but significantly slower on CPU — treat as a fallback.
    """

    async def run(self, image: PILImage) -> OCRResult:
        try:
            image_b64 = _image_to_b64(image)
            text = await ollama_client.vlm_ocr_page(image_b64)
            if not text:
                return OCRResult(
                    text="",
                    confidence=0.0,
                    engine="vlm",
                    error="VLM returned empty output.",
                )
            return OCRResult(text=text, confidence=VLM_CONFIDENCE_PROXY, engine="vlm")
        except Exception as exc:
            logger.error("VLM OCR failed: %s", exc)
            return OCRResult(text="", confidence=0.0, engine="vlm", error=str(exc))
