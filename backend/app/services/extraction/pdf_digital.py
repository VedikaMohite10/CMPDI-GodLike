"""Extractor for digital (text-layer) PDFs using pdfplumber.

Extracts:
  - Text blocks with bounding-box positions (in pts)
  - Tables reconstructed as {headers, rows, shape} JSON
  - Embedded images saved as PNG bytes

All blocking pdfplumber calls run in a thread pool via asyncio.to_thread.
"""
import asyncio
import io
import logging
from typing import Any, Dict, List, Optional

import pdfplumber
from PIL import Image as PILImage

from app.services.extraction.base import (
    AbstractExtractor,
    ExtractionResult,
    ImageAsset,
    Table,
    TextBlock,
)

logger = logging.getLogger(__name__)


def _extract_sync(file_bytes: bytes) -> ExtractionResult:
    """Blocking extraction — runs in thread pool."""
    text_blocks: List[TextBlock] = []
    tables: List[Table] = []
    images: List[ImageAsset] = []
    page_dimensions: Dict[int, tuple] = {}

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page_obj in pdf.pages:
            page_num = page_obj.page_number   # 1-based
            page_dimensions[page_num] = (page_obj.width, page_obj.height)

            # ----------------------------------------------------------
            # Tables — extract before words so table regions can be
            # excluded from free-text extraction if needed
            # ----------------------------------------------------------
            table_idx = 0
            for tbl in page_obj.extract_tables():
                if not tbl:
                    continue
                # First non-empty row treated as headers
                headers = [str(c) if c is not None else "" for c in tbl[0]]
                rows = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in tbl[1:]
                ]
                raw_structure = {
                    "headers": headers,
                    "rows": rows,
                    "shape": [len(rows), len(headers)],
                }
                tables.append(
                    Table(
                        page_number=page_num,
                        table_index=table_idx,
                        raw_structure=raw_structure,
                    )
                )
                table_idx += 1

            # ----------------------------------------------------------
            # Text — extract word-level objects and group by line/block
            # pdfplumber gives us (x0, y0, x1, y1, text) per word
            # ----------------------------------------------------------
            words = page_obj.extract_words()
            if words:
                # Simple grouping: one block per contiguous line cluster
                blocks = _group_words_into_blocks(words)
                for block_idx, (block_text, bbox) in enumerate(blocks):
                    text_blocks.append(
                        TextBlock(
                            page_number=page_num,
                            block_index=block_idx,
                            block_type="paragraph",
                            text=block_text,
                            position={
                                "x0": round(bbox[0], 2),
                                "y0": round(bbox[1], 2),
                                "x1": round(bbox[2], 2),
                                "y1": round(bbox[3], 2),
                            },
                        )
                    )

            # ----------------------------------------------------------
            # Images — extract embedded image objects
            # ----------------------------------------------------------
            img_idx = 0
            for img_meta in page_obj.images:
                try:
                    # pdfplumber exposes raw image data via the underlying page
                    raw_img = _extract_pdfplumber_image(pdf, img_meta)
                    if raw_img:
                        images.append(
                            ImageAsset(
                                page_number=page_num,
                                image_index=img_idx,
                                data=raw_img,
                                format="PNG",
                                width_px=img_meta.get("width"),
                                height_px=img_meta.get("height"),
                                position={
                                    "x0": round(img_meta.get("x0", 0), 2),
                                    "y0": round(img_meta.get("y0", 0), 2),
                                    "x1": round(img_meta.get("x1", 0), 2),
                                    "y1": round(img_meta.get("y1", 0), 2),
                                },
                            )
                        )
                        img_idx += 1
                except Exception as exc:
                    logger.debug("Skipping image on page %d: %s", page_num, exc)

    return ExtractionResult(
        page_count=page_count,
        text_blocks=text_blocks,
        tables=tables,
        images=images,
        page_dimensions=page_dimensions,
    )


def _group_words_into_blocks(words: List[Dict]) -> List[tuple]:
    """Group word dicts into line-level text blocks.

    Strategy: words on the same line (y0 within 2pts) are merged.
    Adjacent lines within 6pts vertical gap form one block.
    Returns list of (text, (x0, y0, x1, y1)).
    """
    if not words:
        return []

    # Sort top-to-bottom, left-to-right
    sorted_words = sorted(words, key=lambda w: (round(w["top"], 0), w["x0"]))

    lines: List[List[Dict]] = []
    current_line: List[Dict] = [sorted_words[0]]

    for word in sorted_words[1:]:
        prev = current_line[-1]
        if abs(word["top"] - prev["top"]) <= 2:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
    lines.append(current_line)

    # Merge lines into blocks (gap ≤ 8pts → same block)
    blocks: List[List[List[Dict]]] = []
    current_block: List[List[Dict]] = [lines[0]]

    for line in lines[1:]:
        prev_bottom = max(w["bottom"] for w in current_block[-1])
        curr_top = min(w["top"] for w in line)
        if curr_top - prev_bottom <= 8:
            current_block.append(line)
        else:
            blocks.append(current_block)
            current_block = [line]
    blocks.append(current_block)

    result = []
    for block_lines in blocks:
        all_words = [w for line in block_lines for w in line]
        text = " ".join(w["text"] for w in all_words)
        x0 = min(w["x0"] for w in all_words)
        y0 = min(w["top"] for w in all_words)
        x1 = max(w["x1"] for w in all_words)
        y1 = max(w["bottom"] for w in all_words)
        result.append((text, (x0, y0, x1, y1)))
    return result


def _extract_pdfplumber_image(pdf: Any, img_meta: Dict) -> Optional[bytes]:
    """Try to extract raw image bytes from a pdfplumber image metadata dict."""
    try:
        import pdfminer.high_level
        # Access underlying pdfminer page image stream
        stream = img_meta.get("stream")
        if stream is None:
            return None
        data = stream.get_data()
        # Convert to PNG via PIL for normalisation
        pil_img = PILImage.open(io.BytesIO(data))
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


class DigitalPDFExtractor(AbstractExtractor):
    """Extractor for text-layer PDFs — uses pdfplumber."""

    async def extract(self, file_bytes: bytes) -> ExtractionResult:
        return await asyncio.to_thread(_extract_sync, file_bytes)
