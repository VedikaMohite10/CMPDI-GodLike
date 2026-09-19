"""Documents router — upload, list, detail, status, original download, image download.

TODO (Phase 3+): Add authentication middleware before these routes.
TODO (Phase 3+): Restrict CORS to known frontend origin.
"""
import asyncio
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.document import Document
from app.models.extraction import ExtractedImage, ExtractedTable, ExtractedTextBlock
from app.models.vector_log import VectorIndexLog
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
    DocumentDetail,
    DocumentStatus,
    DocumentSummary,
    DocumentUploadItem,
    ExtractionSummary,
    UploadResponse,
)
from app.services.ingestion.file_type_detector import detect
from app.services.ingestion.metadata_extractor import infer_report_date
from app.services.ingestion.orchestrator import process_document
from app.services.storage.local_storage import get_storage
from app.utils.file_utils import safe_filename

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload one or more documents",
    description=(
        "Accepts multipart file uploads. Returns immediately with document IDs and 'pending' status. "
        "Processing runs asynchronously — poll GET /documents/{id}/status for progress."
    ),
)
async def upload_documents(
    files: List[UploadFile] = File(..., description="One or more files to ingest."),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    storage = get_storage()
    created_docs: List[DocumentUploadItem] = []

    for upload in files:
        # 1. Read bytes
        raw = await upload.read()
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds max size of {settings.MAX_FILE_SIZE_MB} MB.",
            )

        # 2. Detect file type
        ft_result = detect(raw, upload.filename or "")
        if ft_result.error or ft_result.file_type == "unsupported":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for '{upload.filename}': {ft_result.mime_type}",
            )

        # 3. Generate document ID + storage path
        doc_id = uuid.uuid4()
        ext = Path(upload.filename or "file").suffix or ""
        stored_name = f"{doc_id}{ext}"
        storage_path = f"documents/{stored_name}"
        safe_name = safe_filename(upload.filename or stored_name)

        # 4. Save original file (never overwrite)
        try:
            await storage.save(raw, storage_path)
        except FileExistsError:
            raise HTTPException(status_code=409, detail="Duplicate storage path — try again.")

        # 5. Infer report_date cheaply
        report_date = await asyncio.to_thread(
            infer_report_date, upload.filename or "", raw, ft_result.mime_type
        )

        # 6. Create document record
        doc = Document(
            id=doc_id,
            filename=safe_name,
            original_filename=upload.filename or safe_name,
            file_type=ft_result.file_type,
            mime_type=ft_result.mime_type,
            storage_path=storage_path,
            file_size_bytes=len(raw),
            ocr_required=ft_result.ocr_required,
            report_date=report_date,
            processing_status="pending",
            upload_date=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        await db.flush()

        # 7. Queue background processing
        background_tasks.add_task(process_document, doc_id)

        created_docs.append(
            DocumentUploadItem(
                id=doc_id,
                filename=safe_name,
                file_type=ft_result.file_type,
                processing_status="pending",
                upload_date=doc.upload_date,
            )
        )
        logger.info("Queued processing for document %s (%s).", doc_id, ft_result.file_type)

    await db.commit()
    return UploadResponse(documents=created_docs)


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=PaginatedResponse[DocumentSummary],
    summary="List all documents",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page."),
    status: Optional[str] = Query(None, description="Filter by processing_status."),
    file_type: Optional[str] = Query(None, description="Filter by file_type."),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    count_query = select(func.count(Document.id))

    if status:
        query = query.where(Document.processing_status == status)
        count_query = count_query.where(Document.processing_status == status)
    if file_type:
        query = query.where(Document.file_type == file_type)
        count_query = count_query.where(Document.file_type == file_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Document.upload_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return PaginatedResponse(
        items=[DocumentSummary.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document detail with extraction summary",
)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(document_id, db)

    # Extraction summary counts
    tb_count = await db.execute(
        select(func.count(ExtractedTextBlock.id)).where(
            ExtractedTextBlock.document_id == document_id
        )
    )
    tbl_count = await db.execute(
        select(func.count(ExtractedTable.id)).where(
            ExtractedTable.document_id == document_id
        )
    )
    img_count = await db.execute(
        select(func.count(ExtractedImage.id)).where(
            ExtractedImage.document_id == document_id
        )
    )
    vec_count = await db.execute(
        select(func.count(VectorIndexLog.id)).where(
            VectorIndexLog.document_id == document_id
        )
    )

    summary = ExtractionSummary(
        total_text_blocks=tb_count.scalar_one(),
        total_tables=tbl_count.scalar_one(),
        total_images=img_count.scalar_one(),
        total_vectors_indexed=vec_count.scalar_one(),
    )
    detail = DocumentDetail.model_validate(doc)
    detail.extraction_summary = summary
    return detail


# ---------------------------------------------------------------------------
# GET /documents/{id}/status
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/status",
    response_model=DocumentStatus,
    summary="Lightweight status polling endpoint",
)
async def get_document_status(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(document_id, db)
    return DocumentStatus.model_validate(doc)


# ---------------------------------------------------------------------------
# GET /documents/{id}/original
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/original",
    summary="Download the original unmodified file",
    description=(
        "Streams the original file as stored at upload time. "
        "Satisfies retrieval contract point #4: original document "
        "is retrievable by ID alone, without re-upload."
    ),
)
async def download_original(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doc = await _get_doc_or_404(document_id, db)
    storage = get_storage()

    if not await storage.exists(doc.storage_path):
        raise HTTPException(
            status_code=410,
            detail="Original file is missing from storage. This should not happen — please report.",
        )

    abs_path = storage.absolute_path(doc.storage_path)
    media_type = doc.mime_type or "application/octet-stream"

    return FileResponse(
        path=str(abs_path),
        media_type=media_type,
        filename=doc.original_filename,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}/images/{image_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/images/{image_id}",
    summary="Download an extracted image",
)
async def download_image(
    document_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _get_doc_or_404(document_id, db)

    result = await db.execute(
        select(ExtractedImage).where(
            ExtractedImage.id == image_id,
            ExtractedImage.document_id == document_id,
        )
    )
    img = result.scalar_one_or_none()
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    storage = get_storage()
    if not await storage.exists(img.storage_path):
        raise HTTPException(status_code=410, detail="Image file missing from storage.")

    abs_path = storage.absolute_path(img.storage_path)
    media_type = f"image/{(img.format or 'png').lower()}"
    return FileResponse(path=str(abs_path), media_type=media_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_doc_or_404(document_id: uuid.UUID, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return doc
