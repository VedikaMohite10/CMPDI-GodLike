"""Qdrant vector indexer.

Responsibilities:
  - Ensure the mining_text_blocks collection exists on startup
  - Accept persisted ExtractedTextBlock records, chunk their text,
    embed each chunk via bge-m3, and upsert points to Qdrant
  - Write a VectorIndexLog row for each point so the Qdrant→Postgres
    bridge (retrieval contract point #1) is always maintained

Qdrant point payload stored per point:
  {
    "document_id": str(UUID),
    "page_id":     str(UUID),
    "block_id":    str(UUID),
    "page_number": int,
    "block_type":  str,
    "text_excerpt": str   ← first 500 chars; avoids extra DB lookup in search
  }
"""
import logging
import uuid
from typing import List

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.extraction import ExtractedTextBlock
from app.models.page import Page
from app.models.vector_log import VectorIndexLog
from app.services import ollama_client
from app.services.vector.chunker import chunk_text

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, check_compatibility=False)


async def ensure_collection() -> None:
    """Create the Qdrant collection if it does not already exist.

    Called once on app startup. Safe to call multiple times.
    """
    client = _get_qdrant_client()
    try:
        existing = await client.get_collections()
        names = [c.name for c in existing.collections]
        if settings.QDRANT_COLLECTION_NAME not in names:
            await client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.QDRANT_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'.", settings.QDRANT_COLLECTION_NAME)
        else:
            logger.debug("Qdrant collection '%s' already exists.", settings.QDRANT_COLLECTION_NAME)
    finally:
        await client.close()


async def index_text_blocks(
    blocks: List[ExtractedTextBlock], db: AsyncSession
) -> None:
    """Chunk, embed, and upsert *blocks* to Qdrant; log each point to Postgres.

    Each chunk from the same block shares the block's document_id / page_id /
    block_id provenance — the chunk gets its own Qdrant point_id.
    """
    if not blocks:
        return

    # Build page_number lookup
    page_ids = list({b.page_id for b in blocks})
    page_result = await db.execute(select(Page).where(Page.id.in_(page_ids)))
    pages = {p.id: p.page_number for p in page_result.scalars().all()}

    client = _get_qdrant_client()
    points: List[PointStruct] = []
    log_entries: List[VectorIndexLog] = []

    try:
        for block in blocks:
            chunks = chunk_text(block.text)
            if not chunks:
                continue

            page_number = pages.get(block.page_id, 0)

            for chunk_text_str in chunks:
                try:
                    vector = await ollama_client.embed_text(chunk_text_str)
                except Exception as exc:
                    logger.warning(
                        "Embedding failed for block %s chunk: %s", block.id, exc
                    )
                    continue

                point_id = uuid.uuid4()
                payload = {
                    "document_id": str(block.document_id),
                    "page_id": str(block.page_id),
                    "block_id": str(block.id),
                    "page_number": page_number,
                    "block_type": block.block_type,
                    "text_excerpt": chunk_text_str[:500],
                    "document_filename": "",   # filled in by search endpoint from Postgres
                }
                points.append(
                    PointStruct(id=str(point_id), vector=vector, payload=payload)
                )
                log_entries.append(
                    VectorIndexLog(
                        document_id=block.document_id,
                        page_id=block.page_id,
                        block_id=block.id,
                        qdrant_point_id=point_id,
                    )
                )

        if points:
            await client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points,
            )
            logger.info("Upserted %d vectors to Qdrant.", len(points))

            # Persist log entries (Qdrant → Postgres bridge)
            for entry in log_entries:
                db.add(entry)
            await db.commit()
    finally:
        await client.close()


async def semantic_search(
    query: str,
    top_k: int = 10,
    filter_document_id: str | None = None,
    filter_file_type: str | None = None,
) -> list[dict]:
    """Embed *query* and search Qdrant via REST API (compatible with 1.9.x server).

    Uses raw httpx call to /points/search which is available in Qdrant ≥1.0.
    The newer query_points() endpoint requires server ≥1.10 which we cannot
    guarantee — this approach works on both old and new server versions.
    """
    query_vector = await ollama_client.embed_text(query)

    # Build filter payload
    must_conditions = []
    if filter_document_id:
        must_conditions.append({
            "key": "document_id",
            "match": {"value": filter_document_id}
        })

    body: dict = {
        "vector": query_vector,
        "limit": top_k,
        "with_payload": True,
    }
    if must_conditions:
        body["filter"] = {"must": must_conditions}

    qdrant_url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
    url = f"{qdrant_url}/collections/{settings.QDRANT_COLLECTION_NAME}/points/search"

    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("result", [])
    return [
        {
            "score": r["score"],
            "qdrant_point_id": r["id"],
            **r.get("payload", {}),
        }
        for r in results
    ]

