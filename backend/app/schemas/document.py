"""Pydantic v2 schemas for document endpoints."""
import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class ExtractionSummary(BaseModel):
    """Counts of extracted objects — returned inside DocumentDetail."""
    total_text_blocks: int = 0
    total_tables: int = 0
    total_images: int = 0
    total_vectors_indexed: int = 0


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DocumentUploadItem(BaseModel):
    """One document entry returned immediately after upload (before processing)."""
    id: uuid.UUID
    filename: str
    file_type: str
    processing_status: str
    upload_date: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Response body for POST /documents/upload."""
    documents: List[DocumentUploadItem]


class DocumentSummary(BaseModel):
    """Lightweight document row for list responses."""
    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    upload_date: datetime
    processing_status: str
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None

    model_config = {"from_attributes": True}


class DocumentDetail(BaseModel):
    """Full document metadata returned by GET /documents/{id}."""
    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    mime_type: Optional[str] = None
    upload_date: datetime
    report_date: Optional[date] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    ocr_required: bool
    processing_status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    extraction_summary: ExtractionSummary = Field(default_factory=ExtractionSummary)

    model_config = {"from_attributes": True}


class DocumentStatus(BaseModel):
    """Lightweight status-only response for GET /documents/{id}/status."""
    id: uuid.UUID
    processing_status: str
    processing_error: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
