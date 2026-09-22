"""Extractor for DOCX files using python-docx.

Extracts:
  - Paragraphs → TextBlock (type determined by heading level)
  - Tables → Table with {headers, rows, shape} structure

All documents are mapped to a single logical page (page_number=1)
since DOCX has no inherent page boundaries at the API level.
"""
import asyncio
import io
import logging
from typing import List

import docx
from docx.oxml.ns import qn

from app.services.extraction.base import (
    AbstractExtractor,
    ExtractionResult,
    Table,
    TextBlock,
)

logger = logging.getLogger(__name__)


def _extract_sync(file_bytes: bytes) -> ExtractionResult:
    doc = docx.Document(io.BytesIO(file_bytes))
    text_blocks: List[TextBlock] = []
    tables: List[Table] = []

    page_number = 1   # DOCX → single logical page

    # ------------------------------------------------------------------
    # Paragraphs
    # ------------------------------------------------------------------
    block_idx = 0
    for para_idx, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name.lower() if para.style else ""
        if "heading 1" in style_name:
            block_type = "heading"
        elif "heading" in style_name:
            block_type = "heading"
        elif "list" in style_name:
            block_type = "list_item"
        else:
            block_type = "paragraph"

        text_blocks.append(
            TextBlock(
                page_number=page_number,
                block_index=block_idx,
                block_type=block_type,
                text=text,
                position={"paragraph_index": para_idx},
            )
        )
        block_idx += 1

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    for tbl_idx, tbl in enumerate(doc.tables):
        rows_data: List[List[str]] = []
        for row in tbl.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows_data.append(cells)

        if not rows_data:
            continue

        headers = rows_data[0]
        rows = rows_data[1:]
        raw_structure = {
            "headers": headers,
            "rows": rows,
            "shape": [len(rows), len(headers)],
        }
        tables.append(
            Table(
                page_number=page_number,
                table_index=tbl_idx,
                raw_structure=raw_structure,
                position={"table_index_in_doc": tbl_idx},
            )
        )

    return ExtractionResult(
        page_count=1,
        text_blocks=text_blocks,
        tables=tables,
        images=[],
        page_dimensions={1: (0.0, 0.0)},
    )


class DocxExtractor(AbstractExtractor):
    """python-docx based extractor for .docx files."""

    async def extract(self, file_bytes: bytes) -> ExtractionResult:
        return await asyncio.to_thread(_extract_sync, file_bytes)
