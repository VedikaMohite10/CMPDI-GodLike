"""Search router — POST /search.

Semantic search using bge-m3 embeddings via Qdrant.
No LLM reasoning in this phase — pure vector retrieval.

Every result carries the full provenance chain (retrieval contract point #6):
  qdrant_point_id → block_id → page_id → document_id → storage_path → original file
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.vector.qdrant_indexer import semantic_search

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over extracted text",
    description=(
        "Embeds the query using bge-m3 (local Ollama) and retrieves the top-k "
        "most semantically similar text blocks from Qdrant. "
        "Each result carries document_id, page_id, block_id, and qdrant_point_id "
        "so a future retrieval layer can follow the full chain without re-upload. "
        "No LLM reasoning is applied in this phase."
    ),
)
async def search(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    # 1. Semantic search via Qdrant
    try:
        raw_results = await semantic_search(
            query=request.query,
            top_k=request.top_k,
            filter_document_id=(
                str(request.filter.document_id)
                if request.filter and request.filter.document_id
                else None
            ),
        )
    except Exception as exc:
        logger.error("Qdrant/Ollama search failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Search service unavailable: {exc}",
        )

    if not raw_results:
        return SearchResponse(query=request.query, results=[])

    # 2. Filter by file_type if requested (done in Python since file_type
    #    is in Postgres, not in Qdrant payload)
    if request.filter and request.filter.file_type:
        doc_ids = list({r["document_id"] for r in raw_results})
        doc_result = await db.execute(
            select(Document).where(
                Document.id.in_([uuid.UUID(d) for d in doc_ids]),
                Document.file_type == request.filter.file_type,
            )
        )
        allowed_ids = {str(d.id) for d in doc_result.scalars().all()}
        raw_results = [r for r in raw_results if r["document_id"] in allowed_ids]

    # 3. Enrich with document filename from Postgres
    doc_ids_needed = list({r["document_id"] for r in raw_results})
    doc_result = await db.execute(
        select(Document).where(
            Document.id.in_([uuid.UUID(d) for d in doc_ids_needed])
        )
    )
    doc_map = {str(d.id): d.filename for d in doc_result.scalars().all()}

    # 4. Build response items
    items: list[SearchResultItem] = []
    for r in raw_results:
        items.append(
            SearchResultItem(
                score=float(r["score"]),
                document_id=uuid.UUID(r["document_id"]),
                page_id=uuid.UUID(r["page_id"]),
                block_id=uuid.UUID(r["block_id"]),
                qdrant_point_id=uuid.UUID(str(r["qdrant_point_id"])),
                page_number=int(r.get("page_number", 0)),
                block_type=r.get("block_type", ""),
                text_excerpt=r.get("text_excerpt", "")[:500],
                document_filename=doc_map.get(r["document_id"], ""),
            )
        )

    return SearchResponse(query=request.query, results=items)
