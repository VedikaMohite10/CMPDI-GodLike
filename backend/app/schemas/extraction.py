"""Pydantic v2 schemas for page content endpoint.

Every item carries document_id + page_id to satisfy the provenance requirement.
"""
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TextBlockResponse(BaseModel):
    """One extracted text block with full provenance."""
    id: uuid.UUID
    document_id: uuid.UUID      # → documents.id
    page_id: uuid.UUID          # → pages.id
    block_index: int
    block_type: str
    text: str
    position: Optional[Dict[str, Any]] = None
    char_count: int

    model_config = {"from_attributes": True}


class TableResponse(BaseModel):
    """One extracted table with full structure and provenance."""
    id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    table_index: int
    raw_structure: Dict[str, Any]   # {headers, rows, shape}
    position: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    """One extracted image reference with provenance."""
    id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID
    image_index: int
    download_url: str           # GET /documents/{doc_id}/images/{image_id}
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    format: Optional[str] = None

    model_config = {"from_attributes": True}


class PageContentResponse(BaseModel):
    """Full content of one page — returned by GET /documents/{id}/pages/{n}."""
    document_id: uuid.UUID
    page_id: uuid.UUID
    page_number: int
    text_blocks: List[TextBlockResponse] = []
    tables: List[TableResponse] = []
    images: List[ImageResponse] = []
