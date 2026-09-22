"""Local filesystem storage backend.

Files are stored under STORAGE_ROOT (default: ./storage/).
The directory tree looks like:
  storage/
    documents/  ← original uploaded files (never overwritten)
    images/     ← extracted embedded images (derivatives)

The relative_path stored in the DB is like:
  "documents/abc123.pdf"
  "images/abc123_page1_img0.png"
"""
import asyncio
from pathlib import Path
from functools import lru_cache

import aiofiles

from app.config import get_settings
from app.services.storage.base import AbstractStorageBackend


class LocalStorageBackend(AbstractStorageBackend):
    def __init__(self, root: str | None = None):
        settings = get_settings()
        self._root = Path(root or settings.STORAGE_ROOT).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "documents").mkdir(exist_ok=True)
        (self._root / "images").mkdir(exist_ok=True)

    async def save(self, source_bytes: bytes, relative_path: str) -> str:
        abs_path = self._root / relative_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        if abs_path.exists():
            raise FileExistsError(f"Storage path already occupied: {relative_path}")

        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(source_bytes)

        return relative_path

    async def retrieve(self, relative_path: str) -> bytes:
        abs_path = self._root / relative_path
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found in storage: {relative_path}")
        async with aiofiles.open(abs_path, "rb") as f:
            return await f.read()

    async def exists(self, relative_path: str) -> bool:
        return (self._root / relative_path).exists()

    def absolute_path(self, relative_path: str) -> Path:
        return self._root / relative_path


@lru_cache(maxsize=1)
def get_storage() -> LocalStorageBackend:
    """Return the singleton storage backend."""
    return LocalStorageBackend()
