"""Utility: pagination helpers."""
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")


def paginate(items: List[T], page: int, page_size: int) -> tuple[List[T], int]:
    """Slice *items* for the given page.

    Returns (page_items, total).
    Note: for DB queries, prefer OFFSET/LIMIT in SQL rather than this helper.
    This is kept for in-memory use cases.
    """
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total
