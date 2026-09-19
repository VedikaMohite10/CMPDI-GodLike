"""Package init for vector services."""
from app.services.vector.chunker import chunk_text
from app.services.vector.qdrant_indexer import ensure_collection, index_text_blocks, semantic_search

__all__ = ["chunk_text", "ensure_collection", "index_text_blocks", "semantic_search"]
