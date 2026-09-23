"""Pages router — GET /documents/{id}/pages/{page_number}.

Returns all extracted content for a single page with full provenance
(document_id + page_id on every item).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth.dependencies import get_current_user
from app.models.phase5 import User
from app.models.document import Document
from app.models.extraction import ExtractedImage, ExtractedTable, ExtractedTextBlock
from app.models.page import Page
from app.schemas.extraction import (
    ImageResponse,
    PageContentResponse,
    TableResponse,
    TextBlockResponse,
)

router = APIRouter()


@router.get(
    "/{document_id}/pages/{page_number}",
    response_model=PageContentResponse,
    summary="Get all extracted content for one page",
    description=(
        "Returns text blocks, tables, and images for the specified page. "
        "Every item carries document_id and page_id for downstream provenance tracing."
    ),
)
async def get_page_content(
    document_id: uuid.UUID,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # 1. Verify document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    # 2. Fetch page
    page_result = await db.execute(
        select(Page).where(
            Page.document_id == document_id,
            Page.page_number == page_number,
        )
    )
    page = page_result.scalar_one_or_none()
    if page is None:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found in document {document_id}.",
        )

    # 3. Text blocks
    tb_result = await db.execute(
        select(ExtractedTextBlock)
        .where(ExtractedTextBlock.page_id == page.id)
        .order_by(ExtractedTextBlock.block_index)
    )
    text_blocks: List[TextBlockResponse] = [
        TextBlockResponse(
            id=tb.id,
            document_id=tb.document_id,
            page_id=tb.page_id,
            block_index=tb.block_index,
            block_type=tb.block_type,
            text=tb.text,
            position=tb.position,
            char_count=len(tb.text),
        )
        for tb in tb_result.scalars().all()
    ]

    # 4. Tables
    tbl_result = await db.execute(
        select(ExtractedTable)
        .where(ExtractedTable.page_id == page.id)
        .order_by(ExtractedTable.table_index)
    )
    tables: List[TableResponse] = [
        TableResponse(
            id=t.id,
            document_id=t.document_id,
            page_id=t.page_id,
            table_index=t.table_index,
            raw_structure=t.raw_structure,
            position=t.position,
            caption=t.caption,
        )
        for t in tbl_result.scalars().all()
    ]

    # 5. Images
    img_result = await db.execute(
        select(ExtractedImage)
        .where(ExtractedImage.page_id == page.id)
        .order_by(ExtractedImage.image_index)
    )
    images: List[ImageResponse] = [
        ImageResponse(
            id=img.id,
            document_id=img.document_id,
            page_id=img.page_id,
            image_index=img.image_index,
            download_url=f"/documents/{document_id}/images/{img.id}",
            width_px=img.width_px,
            height_px=img.height_px,
            format=img.format,
        )
        for img in img_result.scalars().all()
    ]

    return PageContentResponse(
        document_id=document_id,
        page_id=page.id,
        page_number=page_number,
        text_blocks=text_blocks,
        tables=tables,
        images=images,
    )
