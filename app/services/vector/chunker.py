"""Text chunker for vector indexing.

Splits a text block into overlapping chunks suitable for bge-m3 embedding.
Uses character-based splitting (not token-based) for simplicity and speed.

bge-m3 max context: 8192 tokens ≈ ~24 000 chars, but shorter chunks yield
better retrieval precision. Target: ~1 500 chars with 200-char overlap.
"""
from typing import List

from app.config import get_settings

settings = get_settings()


def chunk_text(text: str) -> List[str]:
    """Split *text* into overlapping chunks.

    Returns at least one chunk even if text is shorter than chunk_size.
    """
    size = settings.CHUNK_SIZE_CHARS
    overlap = settings.CHUNK_OVERLAP_CHARS

    text = text.strip()
    if not text:
        return []

    if len(text) <= size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap

    return chunks
