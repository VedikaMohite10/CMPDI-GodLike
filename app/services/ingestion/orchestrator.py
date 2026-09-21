"""Ingestion orchestrator — top-level pipeline coordinator.

Called as a FastAPI BackgroundTask after a document is uploaded.
Pipeline:
  1. Update document status → 'processing'
  2. Fetch file bytes from storage
  3. Select and run the appropriate extractor
  4. Persist pages, text blocks, tables, and extracted images to Postgres
  5. Index all text blocks into Qdrant
  6. Update document status → 'done' (or 'failed' on error)

Provenance is guaranteed at DB level: every extraction row has
non-null document_id and page_id (retrieval contract points #2, #3, #5).
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.document import Document
from app.models.extraction import ExtractedImage, ExtractedTable, ExtractedTextBlock
from app.models.page import Page
from app.services.extraction.base import ExtractionResult
from app.services.extraction.docx_extractor import DocxExtractor
from app.services.extraction.image_extractor import ImageExtractor
from app.services.extraction.pdf_digital import DigitalPDFExtractor
from app.services.extraction.pdf_scanned import ScannedPDFExtractor
from app.services.extraction.spreadsheet import SpreadsheetExtractor
from app.services.storage.local_storage import get_storage
from app.services.vector.qdrant_indexer import index_text_blocks

logger = logging.getLogger(__name__)


async def process_document(document_id: uuid.UUID) -> None:
    """Entry point called by the background task after upload.

    Opens its own DB session so it runs independently of the request context.
    """
    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline(document_id, db)
        except Exception as exc:
            logger.exception("Unhandled error processing document %s", document_id)
            await _mark_failed(document_id, str(exc), db)


async def _run_pipeline(document_id: uuid.UUID, db: AsyncSession) -> None:
    # ------------------------------------------------------------------
    # 1. Fetch document record
    # ------------------------------------------------------------------
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        logger.error("Document %s not found — aborting pipeline.", document_id)
        return

    # ------------------------------------------------------------------
    # 2. Mark as processing
    # ------------------------------------------------------------------
    doc.processing_status = "processing"
    doc.updated_at = datetime.now(timezone.utc)
    doc.ingestion_started_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Processing document %s (%s)…", document_id, doc.file_type)

    # ------------------------------------------------------------------
    # 3. Load file bytes from storage
    # ------------------------------------------------------------------
    storage = get_storage()
    file_bytes = await storage.retrieve(doc.storage_path)

    # ------------------------------------------------------------------
    # 4. Select extractor
    # ------------------------------------------------------------------
    extractor = _select_extractor(doc.file_type)
    if extractor is None:
        await _mark_failed(document_id, f"No extractor for file_type={doc.file_type!r}", db)
        return

    # ------------------------------------------------------------------
    # 5. Run extraction
    # ------------------------------------------------------------------
    try:
        extraction: ExtractionResult = await extractor.extract(file_bytes)
    except Exception as exc:
        logger.exception("Extraction failed for %s", document_id)
        await _mark_failed(document_id, f"Extraction error: {exc}", db)
        return

    # ------------------------------------------------------------------
    # 6. Persist pages
    # ------------------------------------------------------------------
    page_map: dict[int, uuid.UUID] = {}   # page_number → page.id
    for page_num in range(1, extraction.page_count + 1):
        dims = extraction.page_dimensions.get(page_num, (None, None))
        page = Page(
            document_id=document_id,
            page_number=page_num,
            width_pts=dims[0],
            height_pts=dims[1],
        )
        db.add(page)
        await db.flush()   # get page.id without full commit
        page_map[page_num] = page.id

    # ------------------------------------------------------------------
    # 7. Persist text blocks
    # ------------------------------------------------------------------
    text_block_records: list[ExtractedTextBlock] = []
    for tb in extraction.text_blocks:
        page_id = page_map.get(tb.page_number)
        if page_id is None:
            logger.warning("TextBlock references unknown page %d — skipping.", tb.page_number)
            continue
        record = ExtractedTextBlock(
            document_id=document_id,
            page_id=page_id,
            block_index=tb.block_index,
            block_type=tb.block_type,
            text=tb.text,
            position=tb.position,
        )
        db.add(record)
        text_block_records.append(record)

    # ------------------------------------------------------------------
    # 8. Persist tables
    # ------------------------------------------------------------------
    for tbl in extraction.tables:
        page_id = page_map.get(tbl.page_number)
        if page_id is None:
            continue
        db.add(
            ExtractedTable(
                document_id=document_id,
                page_id=page_id,
                table_index=tbl.table_index,
                raw_structure=tbl.raw_structure,
                position=tbl.position,
                caption=tbl.caption,
            )
        )

    # ------------------------------------------------------------------
    # 9. Persist extracted images to storage + DB
    # ------------------------------------------------------------------
    for img_asset in extraction.images:
        page_id = page_map.get(img_asset.page_number)
        if page_id is None:
            continue
        img_rel_path = (
            f"images/{document_id}/page{img_asset.page_number}_img{img_asset.image_index}.png"
        )
        try:
            await storage.save(img_asset.data, img_rel_path)
        except FileExistsError:
            pass  # already extracted on a retry

        db.add(
            ExtractedImage(
                document_id=document_id,
                page_id=page_id,
                image_index=img_asset.image_index,
                storage_path=img_rel_path,
                width_px=img_asset.width_px,
                height_px=img_asset.height_px,
                format=img_asset.format or "PNG",
                position=img_asset.position,
            )
        )

    # Flush everything so text block IDs are assigned
    await db.flush()

    # ------------------------------------------------------------------
    # 10. Update document metadata
    # ------------------------------------------------------------------
    doc.page_count = extraction.page_count
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # ------------------------------------------------------------------
    # 11. Vector indexing — chunk + embed + upsert to Qdrant
    # ------------------------------------------------------------------
    try:
        # Re-query text blocks with their IDs now assigned
        tb_result = await db.execute(
            select(ExtractedTextBlock).where(
                ExtractedTextBlock.document_id == document_id
            )
        )
        persisted_blocks = tb_result.scalars().all()
        await index_text_blocks(persisted_blocks, db)
    except Exception as exc:
        logger.error("Vector indexing failed for %s: %s", document_id, exc)
        # Not fatal — document extraction succeeded; mark as done with a warning
        logger.warning("Document %s marked 'done' but vector index may be incomplete.", document_id)

    # ------------------------------------------------------------------
    # 12. Mark done
    # ------------------------------------------------------------------
    doc.processing_status = "done"
    doc.processing_error = None
    doc.updated_at = datetime.now(timezone.utc)
    doc.ingestion_completed_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Document %s processing complete.", document_id)


def _select_extractor(file_type: str):
    """Map internal file_type to the correct extractor instance."""
    return {
        "pdf_digital": DigitalPDFExtractor(),
        "pdf_scanned": ScannedPDFExtractor(),
        "docx": DocxExtractor(),
        "xlsx": SpreadsheetExtractor("xlsx"),
        "csv": SpreadsheetExtractor("csv"),
        "image": ImageExtractor(),
    }.get(file_type)


async def _mark_failed(document_id: uuid.UUID, error: str, db: AsyncSession) -> None:
    await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(
            processing_status="failed",
            processing_error=error[:2000],  # truncate long tracebacks
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    logger.error("Document %s marked failed: %s", document_id, error)
