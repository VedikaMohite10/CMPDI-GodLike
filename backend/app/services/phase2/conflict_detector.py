"""Conflict detector — pure SQL, deterministic.

Runs after all facts for a batch are normalized.
Inserts conflict records for (entity, metric, period) pairs where
values from two different documents materially disagree.
"""
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger    = logging.getLogger(__name__)
settings  = get_settings()


# Base conflict SQL without document filter (used for full-scan)
_CONFLICT_SQL_ALL = """
INSERT INTO conflicts (
    canonical_entity_id, metric, period_start, period_end,
    fact_a_id, fact_b_id,
    value_a, value_b, unit_a, unit_b, delta_pct, status
)
SELECT
    a.canonical_entity_id,
    a.metric,
    LEAST(a.period_start, b.period_start)   AS period_start,
    GREATEST(a.period_end,  b.period_end)   AS period_end,
    a.id   AS fact_a_id,
    b.id   AS fact_b_id,
    a.normalized_value  AS value_a,
    b.normalized_value  AS value_b,
    a.normalized_unit   AS unit_a,
    b.normalized_unit   AS unit_b,
    CASE
        WHEN a.normalized_unit = b.normalized_unit
             AND (a.normalized_value + b.normalized_value) <> 0
        THEN ABS(a.normalized_value - b.normalized_value)
             / ((a.normalized_value + b.normalized_value) / 2.0) * 100
        ELSE NULL
    END AS delta_pct,
    'open' AS status
FROM normalized_facts a
JOIN normalized_facts b
  ON  a.canonical_entity_id = b.canonical_entity_id
  AND a.metric              = b.metric
  AND a.period_start       <= b.period_end
  AND b.period_start       <= a.period_end
  AND a.id                 <  b.id
JOIN extracted_facts efa ON efa.id = a.extracted_fact_id
JOIN extracted_facts efb ON efb.id = b.extracted_fact_id
WHERE efa.document_id      <> efb.document_id
  AND a.normalized_value  IS NOT NULL
  AND b.normalized_value  IS NOT NULL
  AND a.normalized_unit   IS NOT NULL
  AND b.normalized_unit   IS NOT NULL
  AND a.canonical_entity_id IS NOT NULL
  AND a.metric              IS NOT NULL
  AND a.period_start        IS NOT NULL
  AND (
      a.normalized_unit <> b.normalized_unit
      OR ABS(a.normalized_value - b.normalized_value)
         / NULLIF((a.normalized_value + b.normalized_value) / 2.0, 0) * 100
         > :threshold
  )
ON CONFLICT ON CONSTRAINT uq_conflict_pair DO NOTHING
RETURNING id
"""

# With document filter — note: CAST avoids asyncpg type-inference issues
_CONFLICT_SQL_DOC = _CONFLICT_SQL_ALL.replace(
    "ON CONFLICT ON CONSTRAINT uq_conflict_pair DO NOTHING",
    "  AND (\n"
    "      efa.document_id = CAST(:doc_id AS uuid)\n"
    "      OR efb.document_id = CAST(:doc_id AS uuid)\n"
    "  )\n"
    "ON CONFLICT ON CONSTRAINT uq_conflict_pair DO NOTHING",
)


async def detect_conflicts(
    db: AsyncSession,
    document_id: uuid.UUID | None = None,
) -> int:
    """Run conflict detection SQL.

    Args:
        db: async session
        document_id: if provided, only check conflicts involving this document's facts.
                     If None, checks all documents (used for batch processing).
    Returns:
        Number of NEW conflict records inserted.
    """
    threshold = settings.CONFLICT_THRESHOLD_PCT

    if document_id is not None:
        result = await db.execute(
            text(_CONFLICT_SQL_DOC),
            {"threshold": threshold, "doc_id": str(document_id)},
        )
    else:
        result = await db.execute(
            text(_CONFLICT_SQL_ALL),
            {"threshold": threshold},
        )

    new_conflicts = len(result.fetchall())
    await db.flush()

    if new_conflicts:
        logger.info("Conflict detection: %d new conflicts inserted (doc=%s).", new_conflicts, document_id)
    return new_conflicts
