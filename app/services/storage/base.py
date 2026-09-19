"""Storage abstraction — abstract base class.

Callers always interact with this interface, never with the filesystem directly.
Swapping to an S3-compatible backend later requires only a new implementation
file; no calling code changes.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class AbstractStorageBackend(ABC):
    """Minimal interface for document / image storage."""

    @abstractmethod
    async def save(self, source_bytes: bytes, relative_path: str) -> str:
        """Persist bytes at *relative_path* within the storage root.

        Returns the relative_path (stable identifier stored in the DB).
        Raises FileExistsError if the path is already taken.
        """

    @abstractmethod
    async def retrieve(self, relative_path: str) -> bytes:
        """Read and return the file at *relative_path*.

        Raises FileNotFoundError if the path does not exist.
        """

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        """Return True if the file at *relative_path* exists."""

    @abstractmethod
    def absolute_path(self, relative_path: str) -> Path:
        """Return the absolute filesystem path for *relative_path*.

        Used by streaming endpoints that need a Path, not bytes.
        Note: this method intentionally has no async equivalent — callers
        that need to stream should use the absolute path with FastAPI's
        FileResponse / StreamingResponse.
        """
