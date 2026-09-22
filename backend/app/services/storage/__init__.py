"""Package init for storage service."""
from app.services.storage.local_storage import LocalStorageBackend, get_storage

__all__ = ["LocalStorageBackend", "get_storage"]
