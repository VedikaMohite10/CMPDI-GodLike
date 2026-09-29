"""File type detector.

Determines the internal file_type label and whether OCR is required.
Uses the pure-Python `filetype` library for MIME detection (reads magic bytes,
no native system library required — replaces python-magic/libmagic).
For PDFs, opens the file briefly with pdfplumber to check for a text layer.
"""
import io
import logging
from dataclasses import dataclass
from typing import Optional

import filetype as ft

logger = logging.getLogger(__name__)

# Accepted MIME types → internal file_type label (before scanned/digital split)
ACCEPTED_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
    "text/csv": "csv",
    "text/plain": "csv",
    "image/jpeg": "image",
    "image/png": "image",
    "image/tiff": "image",
    "image/bmp": "image",
    "image/webp": "image",
}

# Minimum characters across the first 3 pages to consider a PDF "digital"
_DIGITAL_PDF_CHAR_THRESHOLD = 100


@dataclass
class FileTypeResult:
    mime_type: str
    file_type: str          # pdf_digital | pdf_scanned | docx | xlsx | csv | image
    ocr_required: bool
    error: Optional[str] = None


def detect(file_bytes: bytes, filename: str = "") -> FileTypeResult:
    """Detect MIME type and internal file_type from raw bytes (synchronous).

    Uses magic-byte sniffing via `filetype`; falls back to extension if unknown.
    """
    # 1. MIME detection via magic bytes (pure Python, no libmagic needed)
    kind = ft.guess(file_bytes[:4096])
    if kind is not None:
        mime = kind.mime
    else:
        # filetype couldn't guess — fall back to extension lookup
        mime = _mime_from_extension(filename)
        # Special case: CSV files have no magic bytes; trust extension
        if mime == "application/octet-stream":
            if filename.lower().endswith(".csv"):
                mime = "text/csv"
            else:
                # Unknown binary format — reject rather than silently accept.
                # This prevents .exe, .zip, .bin, etc. from being treated as CSV/plain text.
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "(no extension)"
                return FileTypeResult(
                    mime_type="application/octet-stream",
                    file_type="unsupported",
                    ocr_required=False,
                    error=(
                        f"Unrecognised file format (extension: .{ext}). "
                        "Allowed formats: PDF, DOCX, XLSX, CSV, JPEG, PNG, TIFF, BMP."
                    ),
                )

    # 2. Normalise text/plain → csv if extension says so
    if mime == "text/plain" and filename.lower().endswith(".csv"):
        mime = "text/csv"

    # 3. Map to internal label
    base_type = ACCEPTED_MIMES.get(mime)
    if base_type is None:
        return FileTypeResult(
            mime_type=mime,
            file_type="unsupported",
            ocr_required=False,
            error=f"Unsupported MIME type: {mime}",
        )

    if base_type != "pdf":
        ocr = base_type == "image"
        return FileTypeResult(mime_type=mime, file_type=base_type, ocr_required=ocr)

    # 4. PDF: distinguish digital vs scanned by checking for text layer
    file_type, ocr_required = _classify_pdf(file_bytes)
    return FileTypeResult(mime_type=mime, file_type=file_type, ocr_required=ocr_required)


def _classify_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """Return ('pdf_digital', False) or ('pdf_scanned', True)."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            sample_pages = pdf.pages[:3]
            total_chars = sum(len(p.extract_text() or "") for p in sample_pages)
        return ("pdf_digital", False) if total_chars >= _DIGITAL_PDF_CHAR_THRESHOLD else ("pdf_scanned", True)
    except Exception as exc:
        logger.warning("PDF classification failed, assuming scanned: %s", exc)
        return "pdf_scanned", True


def _mime_from_extension(filename: str) -> str:
    """Fallback MIME from file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "csv": "text/csv",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext, "application/octet-stream")
