"""Duplicate detector — document-level via Qdrant embedding similarity.

Checks for near-duplicate documents by comparing page-level bge-m3 embeddings
already stored in Qdrant from Phase 1.

Detection method: for each page of the new document, search Qdrant for
similar vectors excluding the same document. If a pair of documents share
≥1 page with cosine similarity ≥ threshold, they are flagged as duplicates.

Also detects exact-value fact duplicates (same entity/metric/value/period
across documents) via SQL.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.vector_log import VectorIndexLog
from app.models.phase2 import DuplicateCandidate, NormalizedFact

from app.services.vector.qdrant_indexer import _get_qdrant_client
from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

DOC_SIMILARITY_THRESHOLD  = 0.95   # cosine similarity to flag document duplicates
EXACT_VALUE_ABS_TOLERANCE = 0.0001  # for float comparison in SQL


async def detect_document_duplicates(
    document_id: uuid.UUID, db: AsyncSession
) -> int:
    """Find documents similar to the given document using Qdrant page embeddings.

    Returns number of NEW DuplicateCandidate rows inserted.
    """
    new_count = 0

    # Get all Qdrant point IDs for this document's pages
    result = await db.execute(
        select(VectorIndexLog.qdrant_point_id, VectorIndexLog.block_id)
        .where(VectorIndexLog.document_id == document_id)
        .limit(20)   # check first 20 blocks as representatives
    )
    log_rows = result.all()
    if not log_rows:
        return 0

    client = _get_qdrant_client()

    for row in log_rows:
        point_id = str(row.qdrant_point_id)
        try:
            # Search Qdrant for similar vectors; exclude the current document's points
            hits = await asyncio_qdrant_search(client, point_id, top_k=5)
            for hit in hits:
                other_doc_id = hit.payload.get("document_id") if hit.payload else None
                if not other_doc_id or other_doc_id == str(document_id):
                    continue
                if hit.score < DOC_SIMILARITY_THRESHOLD:
                    continue

                other_uuid = uuid.UUID(other_doc_id)
                # Canonical ordering: smaller UUID first to prevent duplicates
                id_a, id_b = sorted([document_id, other_uuid])

                # Check if already recorded
                existing = await db.execute(
                    select(DuplicateCandidate.id).where(
                        and_(
                            DuplicateCandidate.scope == "document",
                            DuplicateCandidate.document_id_a == id_a,
                            DuplicateCandidate.document_id_b == id_b,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                cand = DuplicateCandidate(
                    scope            = "document",
                    document_id_a    = id_a,
                    document_id_b    = id_b,
                    similarity_score = hit.score,
                    detection_method = "embedding_cosine",
                    status           = "open",
                )
                db.add(cand)
                new_count += 1

        except Exception as exc:
            logger.warning("Qdrant similarity search failed for point %s: %s", point_id, exc)

    if new_count:
        await db.flush()
        logger.info("Found %d new document duplicate candidates for doc %s.", new_count, document_id)

    return new_count


async def detect_fact_duplicates(document_id: uuid.UUID, db: AsyncSession) -> int:
    """Detect exact-value normalized-fact duplicates for facts from this document.

    Two facts are exact-value duplicates if they share the same canonical_entity_id,
    metric, period, and normalized_value (within tolerance) from different documents.
    """
    result = await db.execute(
        text("""
        INSERT INTO duplicate_candidates (scope, fact_id_a, fact_id_b, similarity_score, detection_method, status)
        SELECT 'fact', a.id, b.id, 1.0, 'exact_value_match', 'open'
        FROM normalized_facts a
        JOIN normalized_facts b
          ON  a.canonical_entity_id = b.canonical_entity_id
          AND a.metric              = b.metric
          AND a.normalized_unit     = b.normalized_unit
          AND a.period_start        = b.period_start
          AND a.period_end          = b.period_end
          AND ABS(a.normalized_value - b.normalized_value) < :tol
          AND a.id < b.id
        JOIN extracted_facts efa ON efa.id = a.extracted_fact_id
        JOIN extracted_facts efb ON efb.id = b.extracted_fact_id
        WHERE efa.document_id <> efb.document_id
          AND (efa.document_id = CAST(:doc_id AS uuid) OR efb.document_id = CAST(:doc_id AS uuid))
          AND a.normalized_value IS NOT NULL
          AND a.canonical_entity_id IS NOT NULL
        ON CONFLICT DO NOTHING
        RETURNING id
        """),
        {"doc_id": str(document_id), "tol": EXACT_VALUE_ABS_TOLERANCE},
    )
    new_count = len(result.fetchall())
    if new_count:
        await db.flush()
    return new_count


async def asyncio_qdrant_search(client, point_id: str, top_k: int = 5):
    """Fetch the vector for a point and search for similar ones."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from app.config import get_settings

    s = get_settings()
    collection = s.QDRANT_COLLECTION_NAME

    # Get the actual vector for this point
    points = await client.retrieve(
        collection_name=collection,
        ids=[point_id],
        with_vectors=True,
    )
    if not points:
        return []

    vector = points[0].vector
    if vector is None:
        return []

    results = await client.search(
        collection_name=collection,
        query_vector=vector,
        limit=top_k + 1,  # +1 to exclude self
        with_payload=True,
        score_threshold=DOC_SIMILARITY_THRESHOLD,
    )
    # Exclude the exact same point
    return [r for r in results if str(r.id) != point_id]
