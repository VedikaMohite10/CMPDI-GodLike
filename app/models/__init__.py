"""Package init — import all models so SQLAlchemy/Alembic can see them."""
from app.models.document import Document
from app.models.page import Page
from app.models.extraction import ExtractedTextBlock, ExtractedTable, ExtractedImage
from app.models.vector_log import VectorIndexLog
from app.models.phase2 import (
    CanonicalEntity, EntityAlias, ExtractedFact, NormalizedFact,
    ValidationFlag, Conflict, DuplicateCandidate, FactProcessingLog,
    QueryResponse,
)

__all__ = [
    "Document", "Page", "ExtractedTextBlock", "ExtractedTable", "ExtractedImage",
    "VectorIndexLog",
    "CanonicalEntity", "EntityAlias", "ExtractedFact", "NormalizedFact",
    "ValidationFlag", "Conflict", "DuplicateCandidate", "FactProcessingLog",
    "QueryResponse",
]

