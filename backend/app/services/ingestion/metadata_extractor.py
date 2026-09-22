"""Cheap metadata extractor — infers report_date from filename or PDF metadata.

Only captures what's trivially available; does NOT do NLP inference.
Returns None for report_date if nothing usable is found.
"""
import io
import logging
import re
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# Regex patterns to find dates in filenames — ordered most-specific first
_DATE_PATTERNS = [
    (re.compile(r"(\d{4})[_\-](\d{2})[_\-](\d{2})"), "%Y%m%d"),   # 2023-06-15
    (re.compile(r"(\d{4})[_\-](\d{2})"), "%Y%m"),                   # 2023-06
    (re.compile(r"(\d{4})"), "%Y"),                                  # 2023
]


def infer_report_date(filename: str, file_bytes: bytes, mime_type: str) -> Optional[date]:
    """Try to extract a report date cheaply.

    Order of attempts:
    1. PDF metadata (CreationDate) — if file is a PDF
    2. Filename date pattern matching
    """
    result = None

    # 1. PDF metadata
    if mime_type == "application/pdf":
        result = _date_from_pdf_metadata(file_bytes)

    # 2. Filename
    if result is None:
        result = _date_from_filename(filename)

    return result


def _date_from_pdf_metadata(file_bytes: bytes) -> Optional[date]:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            info = pdf.metadata or {}
            raw = info.get("CreationDate") or info.get("ModDate")
            if raw:
                # PDF date format: D:YYYYMMDDHHmmss
                m = re.search(r"D:(\d{4})(\d{2})(\d{2})", str(raw))
                if m:
                    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception as exc:
        logger.debug("Could not read PDF metadata: %s", exc)
    return None


def _date_from_filename(filename: str) -> Optional[date]:
    stem = filename.rsplit(".", 1)[0]  # remove extension
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(stem)
        if m:
            try:
                groups = m.groups()
                if len(groups) == 3:
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                elif len(groups) == 2:
                    return date(int(groups[0]), int(groups[1]), 1)
                else:
                    return date(int(groups[0]), 1, 1)
            except ValueError:
                continue
    return None
