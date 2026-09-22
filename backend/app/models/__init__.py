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
# Phase 4
from app.models.phase4 import (
    GeneratedReport, TopicCluster, DocumentTopicAssignment, AuditLog,
)
# Phase 5
from app.models.phase5 import (
    User, ParliamentaryQuery, RegionMapping,
    ForecastResult, BenchmarkRun, BenchmarkGroundTruth,
)

__all__ = [
    "Document", "Page", "ExtractedTextBlock", "ExtractedTable", "ExtractedImage",
    "VectorIndexLog",
    "CanonicalEntity", "EntityAlias", "ExtractedFact", "NormalizedFact",
    "ValidationFlag", "Conflict", "DuplicateCandidate", "FactProcessingLog",
    "QueryResponse",
    # Phase 4
    "GeneratedReport", "TopicCluster", "DocumentTopicAssignment", "AuditLog",
    # Phase 5
    "User", "ParliamentaryQuery", "RegionMapping",
    "ForecastResult", "BenchmarkRun", "BenchmarkGroundTruth",
]
