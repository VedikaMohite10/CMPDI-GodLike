"""test_phase1_ingestion.py — Phase 1 as a proper pytest suite.

Replaces the imperative test_phase1.py script with pytest-compatible tests.
Covers all original Phase 1 demo checkpoints:
  1. Upload one of each supported file type → reaches processing_status=done
  2. Extracted content is correctly attributed (document_id / page_id on every row)
  3. GET /search returns results with complete provenance chain
  4. GET /documents/{id}/original returns the exact original file (bytes match)
  5. DB orphan audit: no extraction rows missing document_id or page_id

Run with:
    pytest tests/test_phase1_ingestion.py -v -m integration
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx
import pytest

from tests.conftest import MIME, TIMEOUT, poll_status, upload_and_wait

BASE_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Checkpoint 1 — Upload one of each supported type, confirm status=done
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestUploadAllTypes:
    """Upload every supported file type; confirm all reach processing_status=done."""

    def _upload_one(self, api: httpx.Client, file_path: Path) -> str:
        mime = MIME.get(file_path.suffix, "application/octet-stream")
        doc_id = upload_and_wait(api, file_path, mime=mime, timeout=TIMEOUT)
        assert doc_id is not None, (
            f"Upload/processing failed for {file_path.name} — "
            f"check server logs for errors"
        )
        return doc_id

    def test_upload_digital_pdf(self, api: httpx.Client, doc_pdf_a: Path, require_stack):
        doc_id = self._upload_one(api, doc_pdf_a)
        r = api.get(f"/documents/{doc_id}/status")
        assert r.json()["processing_status"] == "done"

    def test_upload_xlsx(self, api: httpx.Client, doc_xlsx: Path, require_stack):
        doc_id = self._upload_one(api, doc_xlsx)
        r = api.get(f"/documents/{doc_id}/status")
        assert r.json()["processing_status"] == "done"

    def test_upload_csv(self, api: httpx.Client, doc_csv: Path, require_stack):
        doc_id = self._upload_one(api, doc_csv)
        r = api.get(f"/documents/{doc_id}/status")
        assert r.json()["processing_status"] == "done"

    def test_upload_png(self, api: httpx.Client, doc_png: Path, require_stack):
        doc_id = self._upload_one(api, doc_png)
        r = api.get(f"/documents/{doc_id}/status")
        assert r.json()["processing_status"] == "done"

    def test_upload_conflict_pdf(self, api: httpx.Client, doc_pdf_b: Path, require_stack):
        """Upload the intentionally-conflicting PDF B — must also reach done."""
        doc_id = self._upload_one(api, doc_pdf_b)
        r = api.get(f"/documents/{doc_id}/status")
        assert r.json()["processing_status"] == "done"


# ---------------------------------------------------------------------------
# Checkpoint 2 — Extraction rows have correct provenance attributes
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestExtractionProvenance:
    """Every extracted text block, table, and image must have document_id and page_id."""

    def test_text_blocks_have_document_and_page_id(self, api: httpx.Client, doc_pdf_a: Path, require_stack):
        # Upload (may already exist — that's fine, we pick it up from the doc list)
        mime = MIME[doc_pdf_a.suffix]
        with open(doc_pdf_a, "rb") as f:
            r = api.post("/documents/upload", files={"files": (doc_pdf_a.name, f, mime)}, timeout=30)
        assert r.status_code in (200, 202)
        docs = r.json().get("documents", [])
        if not docs:
            pytest.skip("Upload returned no documents")
        doc_id = docs[0]["id"]
        poll_status(api, f"/documents/{doc_id}/status")

        r = api.get(f"/documents/{doc_id}/pages/1", timeout=30)
        assert r.status_code == 200, f"GET /pages/1 returned {r.status_code}"
        page = r.json()

        # Every text block must have non-null document_id and page_id
        blocks = page.get("text_blocks", [])
        for b in blocks:
            assert b.get("document_id") == doc_id, \
                f"text_block missing document_id: {b}"
            assert b.get("page_id") is not None, \
                f"text_block missing page_id: {b}"
            assert b.get("text"), \
                f"text_block has empty text: {b}"

    def test_tables_have_document_and_page_id(self, api: httpx.Client, doc_xlsx: Path, require_stack):
        mime = MIME[doc_xlsx.suffix]
        with open(doc_xlsx, "rb") as f:
            r = api.post("/documents/upload", files={"files": (doc_xlsx.name, f, mime)}, timeout=30)
        assert r.status_code in (200, 202)
        docs = r.json().get("documents", [])
        if not docs:
            pytest.skip("Upload returned no documents")
        doc_id = docs[0]["id"]
        poll_status(api, f"/documents/{doc_id}/status")

        r = api.get(f"/documents/{doc_id}/pages/1", timeout=30)
        assert r.status_code == 200
        page = r.json()

        tables = page.get("tables", [])
        if not tables:
            pytest.skip("No tables extracted from XLSX (may need Phase 2 first)")

        for t in tables:
            assert t.get("document_id") == doc_id, f"table missing document_id: {t}"
            assert t.get("page_id") is not None, f"table missing page_id: {t}"
            raw = t.get("raw_structure", {})
            assert "headers" in raw or "rows" in raw, \
                f"table raw_structure missing headers/rows: {raw}"

    def test_document_detail_has_extraction_summary(self, api: httpx.Client, doc_pdf_a: Path, require_stack):
        # Find any done document
        r = api.get("/documents?status=done&page_size=1", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        if not items:
            pytest.skip("No done documents in DB")

        doc_id = items[0]["id"]
        r = api.get(f"/documents/{doc_id}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "extraction_summary" in d, "Document detail missing extraction_summary"
        summary = d["extraction_summary"]
        assert "total_text_blocks" in summary
        assert "total_tables" in summary
        assert "total_vectors_indexed" in summary


# ---------------------------------------------------------------------------
# Checkpoint 3 — Semantic search returns results with full provenance chain
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestSemanticSearch:
    def test_search_returns_results(self, api: httpx.Client, require_stack):
        r = api.post("/search", json={"query": "coal production mine BCCL", "top_k": 5}, timeout=TIMEOUT)
        assert r.status_code == 200, f"Search returned {r.status_code}: {r.text[:300]}"
        data = r.json()
        assert "results" in data

    def test_search_results_have_full_provenance(self, api: httpx.Client, require_stack):
        r = api.post("/search", json={"query": "coal production", "top_k": 3}, timeout=TIMEOUT)
        assert r.status_code == 200
        results = r.json().get("results", [])
        if not results:
            pytest.skip("No search results — index may be empty")

        hit = results[0]
        assert "document_id" in hit,  f"search result missing document_id: {hit.keys()}"
        assert "page_id"     in hit,  f"search result missing page_id: {hit.keys()}"
        assert "block_id"    in hit,  f"search result missing block_id: {hit.keys()}"
        assert "page_number" in hit,  f"search result missing page_number: {hit.keys()}"
        assert "score"       in hit,  f"search result missing score: {hit.keys()}"

    def test_search_provenance_chain_is_traversable(self, api: httpx.Client, require_stack):
        """Qdrant → Postgres → original: follow the chain from search hit."""
        r = api.post("/search", json={"query": "coal production", "top_k": 1}, timeout=TIMEOUT)
        assert r.status_code == 200
        results = r.json().get("results", [])
        if not results:
            pytest.skip("No search results to trace")

        hit = results[0]
        doc_id = hit["document_id"]
        page_num = hit["page_number"]

        # Postgres: can we fetch the page?
        r2 = api.get(f"/documents/{doc_id}/pages/{page_num}", timeout=15)
        assert r2.status_code == 200, (
            f"Cannot fetch page {page_num} for document {doc_id} from search result. "
            f"Qdrant→Postgres chain broken."
        )

        # Storage: can we fetch the original file?
        r3 = api.get(f"/documents/{doc_id}/original", timeout=30)
        assert r3.status_code == 200, (
            f"Cannot fetch original file for document {doc_id}. "
            f"Postgres→Storage chain broken."
        )

    def test_empty_query_returns_422(self, api: httpx.Client, require_stack):
        r = api.post("/search", json={"query": ""}, timeout=10)
        assert r.status_code == 422

    def test_search_filter_by_file_type(self, api: httpx.Client, require_stack):
        r = api.post(
            "/search",
            json={"query": "coal", "top_k": 5, "filter": {"file_type": "pdf_digital"}},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        # All returned results should have file_type matching the filter
        for hit in r.json().get("results", []):
            if "file_type" in hit:
                assert hit["file_type"] == "pdf_digital"


# ---------------------------------------------------------------------------
# Checkpoint 4 — Original file download: byte-for-byte integrity
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestOriginalFileDownload:
    def test_download_returns_200_and_content_disposition(self, api: httpx.Client, require_stack):
        r = api.get("/documents?status=done&page_size=1", timeout=15)
        items = r.json().get("items", [])
        if not items:
            pytest.skip("No done documents in DB")

        doc_id = items[0]["id"]
        r2 = api.get(f"/documents/{doc_id}/original", timeout=30)
        assert r2.status_code == 200
        assert "content-disposition" in r2.headers
        assert len(r2.content) > 0

    def test_downloaded_file_checksum_matches_uploaded(
        self, api: httpx.Client, doc_csv: Path, require_stack
    ):
        """Upload a CSV, download it back, confirm SHA-256 matches."""
        original_hash = _sha256(doc_csv.read_bytes())

        with open(doc_csv, "rb") as f:
            r = api.post(
                "/documents/upload",
                files={"files": (doc_csv.name, f, "text/csv")},
                timeout=30,
            )
        assert r.status_code in (200, 202)
        docs = r.json().get("documents", [])
        if not docs:
            pytest.skip("Upload returned no documents")

        doc_id = docs[0]["id"]
        poll_status(api, f"/documents/{doc_id}/status")

        r2 = api.get(f"/documents/{doc_id}/original", timeout=30)
        assert r2.status_code == 200
        downloaded_hash = _sha256(r2.content)
        assert downloaded_hash == original_hash, (
            f"Downloaded file hash {downloaded_hash!r} != original {original_hash!r}. "
            f"File integrity violated — original was modified during storage."
        )

    def test_nonexistent_document_returns_404(self, api: httpx.Client, require_stack):
        import uuid
        r = api.get(f"/documents/{uuid.uuid4()}/original", timeout=10)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Checkpoint 5 — List / filter endpoints
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestDocumentList:
    def test_list_returns_paginated_structure(self, api: httpx.Client, require_stack):
        r = api.get("/documents?page=1&page_size=10", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_filter_by_status_done_only_shows_done(self, api: httpx.Client, require_stack):
        r = api.get("/documents?status=done&page_size=50", timeout=15)
        assert r.status_code == 200
        for doc in r.json().get("items", []):
            assert doc["processing_status"] == "done", \
                f"Filter status=done returned doc with status={doc['processing_status']}"

    def test_nonexistent_document_detail_returns_404(self, api: httpx.Client, require_stack):
        import uuid
        r = api.get(f"/documents/{uuid.uuid4()}", timeout=10)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Checkpoint 6 — DB orphan audit (via psql)
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestDBOrphanAudit:
    """Cross-check that no extraction rows exist without proper provenance FKs."""

    def _psql(self, sql: str) -> int:
        from tests.conftest import db_scalar
        try:
            return db_scalar(sql)
        except Exception as e:
            pytest.skip(f"psql not available or DB unreachable: {e}")

    def test_no_text_blocks_without_document_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM extracted_text_blocks WHERE document_id IS NULL"
        )
        assert count == 0, f"{count} text blocks have NULL document_id — provenance broken"

    def test_no_text_blocks_without_page_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM extracted_text_blocks WHERE page_id IS NULL"
        )
        assert count == 0, f"{count} text blocks have NULL page_id — provenance broken"

    def test_no_tables_without_document_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM extracted_tables WHERE document_id IS NULL"
        )
        assert count == 0, f"{count} tables have NULL document_id"

    def test_no_tables_without_page_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM extracted_tables WHERE page_id IS NULL"
        )
        assert count == 0, f"{count} tables have NULL page_id"

    def test_no_documents_without_storage_path(self):
        count = self._psql(
            "SELECT COUNT(*) FROM documents WHERE storage_path IS NULL OR storage_path = ''"
        )
        assert count == 0, \
            f"{count} documents have no storage_path — original file cannot be retrieved"

    def test_no_vector_index_log_missing_block_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM vector_index_log WHERE block_id IS NULL"
        )
        assert count == 0, f"{count} vector_index_log rows missing block_id"

    def test_no_pages_without_document_id(self):
        count = self._psql(
            "SELECT COUNT(*) FROM pages WHERE document_id IS NULL"
        )
        assert count == 0, f"{count} pages missing document_id"
