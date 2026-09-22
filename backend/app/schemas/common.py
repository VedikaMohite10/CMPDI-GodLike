"""Common Pydantic v2 schemas — shared across routers."""
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all 4xx/5xx responses."""
    detail: str
    code: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {"detail": "Document not found.", "code": "NOT_FOUND"}}}


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int
