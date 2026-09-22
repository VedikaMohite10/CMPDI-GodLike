"""Entity resolver — exact → fuzzy (RapidFuzz) → embedding (bge-m3) pipeline.

Resolution levels (in order):
1. Exact match against alias_text (case-insensitive) in entity_aliases table
2. Fuzzy match (RapidFuzz token_sort_ratio ≥ 90) against all alias texts
3. bge-m3 embedding cosine similarity ≥ 0.92 against all alias embeddings
4. Unresolved — stored with method='unresolved', confidence=0.0

New aliases from fuzzy/embedding matches are NOT auto-created in DB — only
exact/manual aliases are persisted during seed. Unresolved stays unresolved.
"""
import asyncio
import logging
import uuid
from typing import Optional

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import CanonicalEntity, EntityAlias
from app.services.ollama_client import embed_text

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD    = 90.0   # RapidFuzz token_sort_ratio (0–100)
EMBEDDING_THRESHOLD = 0.92  # cosine similarity (0.0–1.0)


# In-memory cache of alias→entity loaded per session invocation
_alias_cache: dict[str, tuple[uuid.UUID, str]] = {}   # alias_text_lower → (entity_id, canonical_name)
_alias_texts: list[str] = []


async def _load_aliases(db: AsyncSession) -> None:
    """Populate in-memory alias cache from DB if empty."""
    global _alias_cache, _alias_texts
    if _alias_cache:
        return  # already loaded in this process session
    result = await db.execute(
        select(EntityAlias.alias_text, EntityAlias.canonical_entity_id,
               CanonicalEntity.canonical_name)
        .join(CanonicalEntity, CanonicalEntity.id == EntityAlias.canonical_entity_id)
    )
    for row in result.all():
        _alias_cache[row.alias_text.lower()] = (row.canonical_entity_id, row.canonical_name)
    _alias_texts = list(_alias_cache.keys())
    logger.debug("Loaded %d entity aliases into resolver cache.", len(_alias_cache))


async def resolve_entity(
    raw_text: str, db: AsyncSession
) -> tuple[Optional[uuid.UUID], str, float]:
    """Resolve raw entity text to (canonical_entity_id, method, confidence).

    Returns (None, 'unresolved', 0.0) if no match found.
    """
    if not raw_text or not raw_text.strip():
        return None, "unresolved", 0.0

    await _load_aliases(db)
    needle = raw_text.strip().lower()

    # ── Level 1: Exact match ──────────────────────────────────────────────
    hit = _alias_cache.get(needle)
    if hit:
        return hit[0], "exact", 1.0

    # ── Level 2: Fuzzy match (RapidFuzz) ──────────────────────────────────
    best_score = 0.0
    best_key   = None
    for alias in _alias_texts:
        score = fuzz.token_sort_ratio(needle, alias)
        if score > best_score:
            best_score = score
            best_key   = alias

    if best_score >= FUZZY_THRESHOLD and best_key:
        hit = _alias_cache[best_key]
        logger.debug("Fuzzy resolved %r → %r (%.1f)", raw_text, best_key, best_score)
        return hit[0], "fuzzy", round(best_score / 100.0, 3)

    # ── Level 3: Embedding similarity (bge-m3) ────────────────────────────
    try:
        needle_vec = await embed_text(raw_text.strip())
        best_cos   = -1.0
        best_key   = None

        # Embed all aliases (cached in Ollama's KV; fast on repeat calls)
        for alias in _alias_texts:
            alias_vec = await embed_text(alias)
            cos = _cosine(needle_vec, alias_vec)
            if cos > best_cos:
                best_cos = cos
                best_key = alias

        if best_cos >= EMBEDDING_THRESHOLD and best_key:
            hit = _alias_cache[best_key]
            logger.debug("Embedding resolved %r → %r (%.3f)", raw_text, best_key, best_cos)
            return hit[0], "embedding", round(best_cos, 3)
    except Exception as exc:
        logger.warning("Embedding entity resolution failed for %r: %s", raw_text, exc)

    return None, "unresolved", 0.0


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def invalidate_cache() -> None:
    """Call this if the entity_aliases table is modified at runtime."""
    global _alias_cache, _alias_texts
    _alias_cache = {}
    _alias_texts = []
