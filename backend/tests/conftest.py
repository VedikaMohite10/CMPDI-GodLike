"""Shared conftest for the CMPDI full-system integration test suite.

All synthetic test documents are generated HERE programmatically — no binary
files committed to the repository. Generators use libraries already installed
in the project (reportlab, openpyxl, Pillow).

Usage:
    pytest tests/ -v                         # all tests (needs running stack)
    pytest tests/ -m "not integration" -v   # unit-safe tests only
    pytest tests/ -m integration -v         # only integration tests

Marks:
    integration   — requires running API + Postgres + Qdrant (+ Ollama for LLM tests)
    llm           — additionally requires Ollama with the configured models loaded
"""
from __future__ import annotations

import io
import os
import struct
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Generator, Optional

import pytest
import httpx

# ---------------------------------------------------------------------------
# Environment defaults — can be overridden by .env
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")
DB_URL   = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://cmpdi:cmpdipass@localhost:5432/cmpdi_mining",
)
os.environ.setdefault("DATABASE_URL", DB_URL)

TIMEOUT = int(os.environ.get("CMPDI_TEST_TIMEOUT", "300"))   # seconds, LLM calls are slow on CPU
POLL_INTERVAL = 3   # seconds between status polls

# ---------------------------------------------------------------------------
# pytest marks
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires running CMPDI stack")
    config.addinivalue_line("markers", "llm: additionally requires Ollama with models loaded")


# ---------------------------------------------------------------------------
# HTTP client (synchronous — used by all non-async tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def api() -> Generator[httpx.Client, None, None]:
    """Synchronous httpx client pointing at the running API."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


# ---------------------------------------------------------------------------
# Stack reachability guard — skip integration tests if API is not up
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=False)
def require_stack(api: httpx.Client):
    """Mark integration tests; skip entire session if API is unreachable."""
    try:
        r = api.get("/health", timeout=5)
        if r.status_code != 200:
            pytest.skip(f"API returned {r.status_code} — stack not healthy")
    except httpx.ConnectError:
        pytest.skip(f"API not reachable at {BASE_URL} — start the stack first")


# ---------------------------------------------------------------------------
# Synthetic fixture document generators
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text_lines: list[str]) -> bytes:
    """Build a minimal valid PDF containing text_lines without reportlab.

    Uses a hand-crafted minimal PDF structure so the test suite works even
    without reportlab. If reportlab IS available it uses that instead for
    richer content (tables etc.).
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        y = 780
        for line in text_lines:
            c.drawString(40, y, line)
            y -= 18
            if y < 60:
                c.showPage()
                y = 780
        c.save()
        return buf.getvalue()
    except ImportError:
        # Fallback: hand-craft the smallest valid PDF
        body = b"%PDF-1.4\n"
        body += b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        body += b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        content = b"BT /F1 12 Tf 40 750 Td "
        for line in text_lines:
            safe = line.replace("(", "\\(").replace(")", "\\)").encode()
            content += b"(" + safe + b") Tj T*\n"
        content += b"ET"
        body += b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        body += b"/Contents 4 0 R /Resources <</Font <</F1 <</Type /Font "
        body += b"/Subtype /Type1 /BaseFont /Helvetica>>>>>>>>\nendobj\n"
        body += b"4 0 obj\n<</Length " + str(len(content)).encode() + b">>\nstream\n"
        body += content + b"\nendstream\nendobj\n"
        body += b"xref\n0 5\n0000000000 65535 f \n"
        body += b"trailer\n<</Size 5 /Root 1 0 R>>\nstartxref\n9\n%%EOF\n"
        return body


def make_digital_pdf_a(tmp_path: Path) -> Path:
    """PDF A — coal production report for BCCL, Moonidih Colliery, FY2023.
    Values: coal_production=2.1 MT, ob_removal=4.8 MCM.
    """
    lines = [
        "COAL PRODUCTION REPORT — BCCL FY2023 (OFFICIAL)",
        "",
        "Subsidiary: Bharat Coking Coal Limited (BCCL)",
        "Mine: Moonidih Colliery",
        "Period: FY2022-23 (April 2022 – March 2023)",
        "",
        "Coal Production: 2.1 MT",
        "OB Removal: 4.8 MCM",
        "Status: Active",
        "",
        "Note: Production figures are audited and final.",
    ]
    p = tmp_path / "digital_report_a.pdf"
    p.write_bytes(_make_minimal_pdf(lines))
    return p


def make_digital_pdf_b(tmp_path: Path) -> Path:
    """PDF B — INTENTIONAL CONFLICT: same entity/metric/period, value=2.8 MT.

    This document is the second report submitted for the same mine and period.
    It creates a deliberate conflict with PDF A (2.1 MT vs 2.8 MT).
    """
    lines = [
        "COAL PRODUCTION SUMMARY — BCCL Q4 2023 ESTIMATE",
        "",
        "Company: Bharat Coking Coal Limited (BCCL)",
        "Mine: Moonidih Colliery",
        "Period: FY2022-23 (April 2022 – March 2023)",
        "",
        "Estimated Production: 2.8 MT",
        "OB Removal: 4.8 MCM",
        "",
        "CAUTION: This is a preliminary estimate pending audit.",
    ]
    p = tmp_path / "digital_report_b.pdf"
    p.write_bytes(_make_minimal_pdf(lines))
    return p


def make_production_xlsx(tmp_path: Path) -> Path:
    """XLSX with a structured production table including multiple mines."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Coal Production FY2023"
    ws.append(["Mine Name", "Subsidiary", "Production (MT)", "OB Removal (MCM)", "Status"])
    ws.append(["Moonidih Colliery",  "BCCL", 2.1, 4.8, "Active"])
    ws.append(["Jharia Division",    "BCCL", 5.4, 11.2, "Active"])
    ws.append(["Sijua Area",         "BCCL", 3.0, 8.5, "Active"])
    ws.append(["Rajrappa Colliery",  "CCL",  1.9, 3.4, "Active"])
    ws.append(["Magadh Colliery",    "CCL",  4.2, 9.1, "Active"])
    p = tmp_path / "production_data.xlsx"
    wb.save(str(p))
    return p


def make_survey_csv(tmp_path: Path) -> Path:
    """CSV with numeric survey data including a deliberate outlier (999 MT).

    The outlier should trigger a Phase 2 validation flag (z-score anomaly).
    """
    rows = [
        "mine_name,production_mt,year",
        "Moonidih Colliery,2.1,2023",
        "Jharia Division,5.4,2023",
        "Sijua Area,3.0,2023",
        "Rajrappa Colliery,1.9,2023",
        "Magadh Colliery,4.2,2023",
        # Deliberate outlier — 999 MT is statistically impossible
        "SYNTHETIC_OUTLIER_MINE,999.0,2023",
    ]
    p = tmp_path / "survey_data.csv"
    p.write_text("\n".join(rows))
    return p


def make_ocr_png(tmp_path: Path) -> Path:
    """PNG image containing text rendered with PIL.

    Falls back to a minimal valid PNG (1×1 pixel) if PIL not available.
    OCR extraction should find the text; a synthetic high-value triggers a flag.
    """
    p = tmp_path / "ocr_report.png"
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (800, 400), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20),  "OCR TEST REPORT — SYNTHETIC", fill="black")
        draw.text((20, 60),  "Mine: OCR Test Mine", fill="black")
        draw.text((20, 100), "Production: 1.5 MT", fill="black")
        draw.text((20, 140), "Period: FY2022-23", fill="black")
        img.save(str(p), format="PNG")
    except (ImportError, Exception):
        # Minimal valid 1x1 PNG
        p.write_bytes(
            b"\x89PNG\r\n\x1a\n"              # signature
            b"\x00\x00\x00\rIHDR"            # IHDR length + type
            b"\x00\x00\x00\x01"              # width=1
            b"\x00\x00\x00\x01"              # height=1
            b"\x08\x02\x00\x00\x00"          # 8-bit RGB
            b"\x90wS\xde"                    # CRC (pre-computed)
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    return p


def make_empty_pdf(tmp_path: Path) -> Path:
    """PDF with a single blank page — for edge-case empty-document testing."""
    lines = [""]
    p = tmp_path / "empty_doc.pdf"
    p.write_bytes(_make_minimal_pdf(lines))
    return p


def make_corrupted_bin(tmp_path: Path) -> Path:
    """Random binary garbage — not a valid document of any supported type."""
    p = tmp_path / "corrupted_doc.bin"
    p.write_bytes(b"\x00\x01\x02\x03NOTAPDF" + bytes(range(256)) * 4)
    return p


# ---------------------------------------------------------------------------
# Polling helper (used by integration tests)
# ---------------------------------------------------------------------------

def poll_status(
    api: httpx.Client,
    url: str,
    *,
    done_values: tuple = ("done", "complete"),
    fail_values: tuple = ("failed",),
    timeout: int = TIMEOUT,
    interval: int = POLL_INTERVAL,
) -> tuple[str, dict]:
    """Poll url until status is done/failed or timeout.

    Returns (status_string, full_response_body).
    """
    deadline = time.time() + timeout
    last_body: dict = {}
    while time.time() < deadline:
        try:
            r = api.get(url, timeout=30)
            if r.status_code == 200:
                last_body = r.json()
                status = last_body.get("status", last_body.get("processing_status", ""))
                if status in done_values:
                    return status, last_body
                if status in fail_values:
                    return status, last_body
        except Exception:
            pass
        time.sleep(interval)
    return "timeout", last_body


# ---------------------------------------------------------------------------
# DB session helper (synchronous via asyncio.run for cross-check assertions)
# ---------------------------------------------------------------------------

def db_scalar(sql: str) -> int:
    """Run a raw COUNT query via psql subprocess and return the integer result.

    Used for cross-checking dashboard numbers against raw DB queries without
    pulling all rows into Python memory.

    Requires: psql on PATH and Postgres running at localhost:5432.
    """
    import subprocess
    env = dict(os.environ, PGPASSWORD="cmpdipass")
    res = subprocess.run(
        ["psql", "-h", "localhost", "-U", "cmpdi", "-d", "cmpdi_mining", "-t", "-A", "-c", sql],
        capture_output=True, text=True, env=env, timeout=15,
    )
    raw = res.stdout.strip()
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"psql query returned non-integer: {raw!r}\nStderr: {res.stderr}")


# ---------------------------------------------------------------------------
# Fixtures: tmp_path-scoped synthetic documents (session-scope for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("cmpdi_fixtures")


@pytest.fixture(scope="session")
def doc_pdf_a(fixture_dir) -> Path:
    return make_digital_pdf_a(fixture_dir)


@pytest.fixture(scope="session")
def doc_pdf_b(fixture_dir) -> Path:
    return make_digital_pdf_b(fixture_dir)


@pytest.fixture(scope="session")
def doc_xlsx(fixture_dir) -> Path:
    return make_production_xlsx(fixture_dir)


@pytest.fixture(scope="session")
def doc_csv(fixture_dir) -> Path:
    return make_survey_csv(fixture_dir)


@pytest.fixture(scope="session")
def doc_png(fixture_dir) -> Path:
    return make_ocr_png(fixture_dir)


@pytest.fixture(scope="session")
def doc_empty_pdf(fixture_dir) -> Path:
    return make_empty_pdf(fixture_dir)


@pytest.fixture(scope="session")
def doc_corrupted(fixture_dir) -> Path:
    return make_corrupted_bin(fixture_dir)


# ---------------------------------------------------------------------------
# Upload helper — returns document ID after Phase 1 ingestion is complete
# ---------------------------------------------------------------------------

def upload_and_wait(
    api: httpx.Client,
    file_path: Path,
    mime: str = "application/pdf",
    *,
    timeout: int = TIMEOUT,
) -> Optional[str]:
    """Upload a file and poll until processing_status = done. Returns document_id or None."""
    with open(file_path, "rb") as f:
        r = api.post(
            "/documents/upload",
            files={"files": (file_path.name, f, mime)},
            timeout=30,
        )
    if r.status_code not in (200, 202):
        return None
    docs = r.json().get("documents", [])
    if not docs:
        return None
    doc_id = docs[0]["id"]
    status, _ = poll_status(api, f"/documents/{doc_id}/status", timeout=timeout)
    return doc_id if status == "done" else None


MIME = {
    ".pdf":  "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv":  "text/csv",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".bin":  "application/octet-stream",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
