"""Pydantic v2 schemas for POST /search.

Search results carry the full provenance chain:
  qdrant_point_id → block_id → page_id → document_id → storage_path → original file
This satisfies retrieval contract point #6.
"""
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchFilter(BaseModel):
    """Optional filters to scope a semantic search."""
    document_id: Optional[uuid.UUID] = Field(
        None, description="Restrict search to a single document."
    )
    file_type: Optional[str] = Field(
        None, description="Restrict search by file type (e.g. 'pdf_digital')."
    )


class SearchRequest(BaseModel):
    """Request body for POST /search."""
    query: str = Field(..., min_length=1, description="Natural-language search query.")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return.")
    filter: Optional[SearchFilter] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "coal production Jharia 2023",
                "top_k": 5,
                "filter": {"file_type": "pdf_digital"},
            }
        }
    }


class SearchResultItem(BaseModel):
    """One search hit with full provenance for downstream retrieval.

    A future retrieval layer can follow:
      qdrant_point_id → block_id  → GET /documents/{document_id}/pages/{page_number}
      document_id                 → GET /documents/{document_id}/original
    No re-upload is required.
    """
    score: float                    # cosine similarity from Qdrant (0–1)
    document_id: uuid.UUID          # → PostgreSQL documents.id
    page_id: uuid.UUID              # → PostgreSQL pages.id
    block_id: uuid.UUID             # → PostgreSQL extracted_text_blocks.id
    qdrant_point_id: uuid.UUID      # Qdrant point identifier (for debugging)
    page_number: int                # human-readable; avoids extra lookup
    block_type: str
    text_excerpt: str               # first 500 chars of the text block
    document_filename: str


class SearchResponse(BaseModel):
    """Response body for POST /search."""
    query: str
    results: List[SearchResultItem]
