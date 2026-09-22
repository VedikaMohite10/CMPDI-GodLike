"""Package init for schemas."""
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.document import (
    DocumentDetail,
    DocumentStatus,
    DocumentSummary,
    DocumentUploadItem,
    ExtractionSummary,
    UploadResponse,
)
from app.schemas.extraction import (
    ImageResponse,
    PageContentResponse,
    TableResponse,
    TextBlockResponse,
)
from app.schemas.search import SearchFilter, SearchRequest, SearchResponse, SearchResultItem

__all__ = [
    "ErrorResponse",
    "PaginatedResponse",
    "DocumentDetail",
    "DocumentStatus",
    "DocumentSummary",
    "DocumentUploadItem",
    "ExtractionSummary",
    "UploadResponse",
    "ImageResponse",
    "PageContentResponse",
    "TableResponse",
    "TextBlockResponse",
    "SearchFilter",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
]
