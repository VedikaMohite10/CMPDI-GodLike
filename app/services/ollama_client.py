"""Shared async Ollama HTTP client.

All Ollama calls (embeddings + VLM) go through this module so there is one
place to configure timeouts, retry logic, and the base URL.

Endpoint reference:
  POST /api/embeddings  → text embedding
  POST /api/chat        → multimodal vision (VLM)
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def embed_text(text: str) -> List[float]:
    """Embed a single string using bge-m3 via Ollama.

    Returns a 1024-dimensional float vector.
    Raises httpx.HTTPStatusError on Ollama API errors.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {"model": settings.EMBEDDING_MODEL, "prompt": text}

    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        embedding: List[float] = data["embedding"]
        return embedding


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple strings sequentially.

    Ollama's /api/embeddings endpoint is one-at-a-time; we loop here.
    A future phase could batch via the /api/embed endpoint if available.
    """
    results = []
    for text in texts:
        vec = await embed_text(text)
        results.append(vec)
    return results


async def vlm_ocr_page(image_b64: str, prompt: str | None = None) -> str:
    """Send a base64-encoded page image to qwen2.5vl via Ollama chat API.

    Returns the model's text response (OCR output).
    """
    if prompt is None:
        prompt = (
            "You are an OCR assistant. Extract ALL text from this image exactly as it appears. "
            "Preserve line breaks, numbers, and special characters. "
            "Do not summarise or interpret — output only the raw extracted text."
        )

    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": settings.VLM_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
        logger.debug("Calling VLM OCR via Ollama (model=%s)…", settings.VLM_MODEL)
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text: str = data["message"]["content"]
        return text.strip()
