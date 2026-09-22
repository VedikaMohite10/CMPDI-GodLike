"""test_edge_cases.py — Systematic edge case coverage.

Tests:
  1. Corrupted / unreadable file → clear error, not crash or silent done
  2. Empty / near-empty document → graceful handling, not a crash
  3. Query for nonexistent entity/metric/period → clear no-data response
  4. Report for scope with no data → graceful, not broken-but-claiming-success
  5. Two simultaneous corrections to the same fact → audit log captures both,
     final state is deterministic
  6. Non-existent document operations → correct 404 responses
  7. Invalid request bodies → correct 422 validation errors

Run with:
    pytest tests/test_edge_cases.py -v -m integration
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

import httpx
import pytest

from tests.conftest import MIME, TIMEOUT, db_scalar, poll_status

BASE_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# 1. Corrupted file → clear error, not crash or silent done
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestCorruptedFile:
    def test_corrupted_binary_does_not_crash_server(
        self, api: httpx.Client, doc_corrupted: Path, require_stack
    ):
        """Upload random binary garbage. Server must return an error response
        or silently mark the document as 'failed' — never 'done' with empty data,
        and never a 500 crash."""
        with open(doc_corrupted, "rb") as f:
            r = api.post(
                "/documents/upload",
                files={"files": (doc_corrupted.name, f, "application/octet-stream")},
                timeout=30,
            )
        # Either rejected at upload time (400/415/422) or accepted and later failed
        if r.status_code in (400, 415, 422):
            # Correctly rejected upfront — ideal behavior
            return

        assert r.status_code in (200, 202), (
            f"Upload returned unexpected {r.status_code}: {r.text[:200]}"
        )
        docs = r.json().get("documents", [])
        if not docs:
            pytest.skip("Upload returned no document IDs")

        doc_id = docs[0]["id"]

        # Poll until status is final
        status, body = poll_status(
            api, f"/documents/{doc_id}/status",
            done_values=("done", "failed"), fail_values=(),
            timeout=120,
        )
        assert status == "failed", (
            f"Corrupted file reached status='{status}' instead of 'failed'. "
            f"A document with unreadable content must never be marked 'done'. "
            f"Response body: {body}"
        )

    def test_corrupted_file_failure_includes_error_message(
        self, api: httpx.Client, doc_corrupted: Path, require_stack
    ):
        """When a corrupted file fails, the status response must include an
        error message — not an empty or null processing_error field."""
        with open(doc_corrupted, "rb") as f:
            r = api.post(
                "/documents/upload",
                files={"files": (doc_corrupted.name, f, "application/octet-stream")},
                timeout=30,
            )
        if r.status_code not in (200, 202):
            return  # Already rejected — no status to check

        docs = r.json().get("documents", [])
        if not docs:
            return

        doc_id = docs[0]["id"]
        poll_status(api, f"/documents/{doc_id}/status", timeout=120)

        r2 = api.get(f"/documents/{doc_id}/status", timeout=15)
        body = r2.json()
        if body.get("processing_status") == "failed":
            assert body.get("processing_error"), (
                f"Document failed but processing_error is empty: {body}. "
                f"Error message required for diagnostics."
            )


# ---------------------------------------------------------------------------
# 2. Empty / near-empty document → graceful handling
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestEmptyDocument:
    def test_empty_pdf_does_not_crash_server(
        self, api: httpx.Client, doc_empty_pdf: Path, require_stack
    ):
        """An empty PDF (1 blank page) must be handled gracefully.
        The document should reach 'done' (with 0 text blocks extracted)
        or 'failed' with an informative error — but NEVER a server crash (500)."""
        with open(doc_empty_pdf, "rb") as f:
            r = api.post(
                "/documents/upload",
                files={"files": (doc_empty_pdf.name, f, "application/pdf")},
                timeout=30,
            )
        # Some servers may reject PDFs with no extractable content
        if r.status_code in (400, 422):
            return

        assert r.status_code in (200, 202), f"Unexpected {r.status_code}: {r.text[:200]}"
        docs = r.json().get("documents", [])
        if not docs:
            return

        doc_id = docs[0]["id"]
        status, _ = poll_status(api, f"/documents/{doc_id}/status", timeout=120)

        # Either done (empty extraction) or failed (no extractable content)
        assert status in ("done", "failed"), (
            f"Empty PDF reached unexpected status '{status}'."
        )

        # If done, extraction summary must show zero or very few blocks
        if status == "done":
            r2 = api.get(f"/documents/{doc_id}", timeout=15)
            if r2.status_code == 200:
                summary = r2.json().get("extraction_summary", {})
                block_count = summary.get("total_text_blocks", 999)
                assert block_count <= 5, (
                    f"Empty PDF shows {block_count} text blocks — something extracted "
                    f"content from a blank page incorrectly."
                )


# ---------------------------------------------------------------------------
# 3. Query with no underlying data → clear no-data, not fabricated answer
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.llm
class TestQueryNoData:
    def test_query_for_nonexistent_entity_returns_ie_not_error(
        self, api: httpx.Client, require_stack
    ):
        """Query for an entity that does not exist in the system."""
        r = api.post("/query", json={
            "question": "What is the coal production of FICTITIOUS_MINE_XYZ_DOES_NOT_EXIST?",
            "top_k_semantic": 3,
        }, timeout=TIMEOUT)
        # Must be 200 with insufficient-evidence, or 404
        if r.status_code == 404:
            return
        assert r.status_code == 200
        body = r.json()
        reasoning = body.get("reasoning_type", "")
        assert reasoning == "insufficient-evidence", (
            f"Query for a nonexistent entity returned reasoning_type='{reasoning}'. "
            f"Expected 'insufficient-evidence'. Answer: {body.get('answer', '')[:200]}"
        )

    def test_analytics_compare_for_no_data_returns_404(self, api: httpx.Client, require_stack):
        """/analytics/compare for a non-existent entity must return 404."""
        r = api.post("/analytics/compare", json={
            "entity_ids": [str(uuid.uuid4())],
            "metric": "coal_production",
            "period_start_year": 2020,
            "period_end_year": 2023,
        }, timeout=30)
        assert r.status_code == 404, (
            f"Expected 404 for nonexistent entity_id, got {r.status_code}: {r.text}"
        )

    def test_analytics_trend_for_no_data_returns_404(self, api: httpx.Client, require_stack):
        r = api.post("/analytics/trend", json={
            "entity_id": str(uuid.uuid4()),
            "metric": "coal_production",
            "period_start_year": 2020,
            "period_end_year": 2023,
        }, timeout=30)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 4. Report for scope with no data → graceful, not broken-but-claiming-success
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.llm
class TestReportNoData:
    def test_report_for_future_scope_handles_no_data_gracefully(
        self, api: httpx.Client, require_stack
    ):
        """Generate a report for a far-future date range where no data can exist.
        The system must either return an error or a valid report with empty sections —
        NOT a report claiming to have findings for data that doesn't exist."""
        r = api.post("/reports/generate", json={
            "period_start": "2080-01-01",
            "period_end":   "2090-12-31",
            "label":        "Edge Case: Future Report (No Data)",
        }, timeout=TIMEOUT)

        if r.status_code in (400, 404, 422):
            return  # Correctly rejected

        assert r.status_code in (200, 202), f"Unexpected {r.status_code}: {r.text[:200]}"
        body = r.json()
        report_id = body.get("report_id")
        if not report_id:
            return

        r2 = api.get(f"/reports/{report_id}", timeout=30)
        if r2.status_code != 200:
            return

        content = r2.json().get("content") or {}

        # The report must NOT claim meaningful production figures for 2080-2090
        # It should either have empty sections or explicit no-data warnings
        warnings = content.get("data_quality_warnings", {})
        citations = content.get("citations", [])

        # If citations exist for a future date, that's a fabrication
        for c in citations:
            fact_year = str(c.get("period", "")).strip()
            if fact_year and int(fact_year[:4]) > 2024:
                pytest.fail(
                    f"Report for 2080-2090 scope contains a citation for year {fact_year}. "
                    f"No real data exists for this period — this is a fabricated citation."
                )


# ---------------------------------------------------------------------------
# 5. Concurrent corrections to the same fact — both must be recorded
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestConcurrentCorrections:
    """Submit two corrections to the same fact in rapid succession.
    Both must appear in the audit log. The final state must be deterministic."""

    def test_two_corrections_both_logged(self, api: httpx.Client, require_stack):
        # Find an open flag
        r = api.get("/review/flags?status=open&page_size=1", timeout=15)
        if r.status_code != 200:
            pytest.skip("Review flags endpoint not available")
        flags = r.json().get("items", [])
        if not flags:
            pytest.skip("No open flags for concurrent correction test")

        flag_id = flags[0]["id"]
        results: list[httpx.Response] = []

        def correct(value: float, reviewer: str):
            r = api.post(f"/review/flags/{flag_id}/correct", json={
                "corrected_value": value,
                "corrected_unit":  "MT",
                "reviewer":        reviewer,
                "note":            f"Concurrent correction test by {reviewer}",
            }, timeout=30)
            results.append(r)

        # Fire both corrections concurrently
        t1 = threading.Thread(target=correct, args=(1.1, "reviewer_alpha"))
        t2 = threading.Thread(target=correct, args=(2.2, "reviewer_beta"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Both must have returned valid responses (200)
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 1, (
            f"Both concurrent corrections failed. "
            f"Responses: {[r.status_code for r in results]}"
        )

        # If both succeeded, the audit log must contain at least 2 correction entries
        # for this fact
        r2 = api.get(
            f"/review/audit-log?action_type=correct&page_size=50",
            timeout=15,
        )
        assert r2.status_code == 200
        entries = r2.json().get("items", [])
        flag_entries = [e for e in entries if e.get("target_id") == flag_id]

        if success_count == 2:
            assert len(flag_entries) >= 2, (
                f"Both corrections succeeded but only {len(flag_entries)} audit log "
                f"entries found for flag {flag_id}. Both corrections must be logged."
            )

        # The final state must be deterministic — normalized_value must be one of the two
        # correction values, not a mix or undefined
        fact_r = api.get(f"/facts/{flags[0].get('normalized_fact_id', uuid.uuid4())}/evidence",
                         timeout=15)
        if fact_r.status_code == 200:
            final_val = fact_r.json().get("fact", {}).get("normalized_value")
            assert final_val in (1.1, 2.2, None), (
                f"Final normalized_value={final_val} is not one of the two correction values. "
                f"Concurrent correction produced an indeterminate state."
            )


# ---------------------------------------------------------------------------
# 6. Non-existent document operations → 404
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestNonexistentResourceHandling:
    def test_nonexistent_document_status_returns_404(self, api: httpx.Client, require_stack):
        r = api.get(f"/documents/{uuid.uuid4()}/status", timeout=10)
        assert r.status_code == 404

    def test_nonexistent_document_pages_returns_404(self, api: httpx.Client, require_stack):
        r = api.get(f"/documents/{uuid.uuid4()}/pages/1", timeout=10)
        assert r.status_code == 404

    def test_nonexistent_fact_evidence_returns_404(self, api: httpx.Client, require_stack):
        r = api.get(f"/facts/{uuid.uuid4()}/evidence", timeout=10)
        assert r.status_code == 404

    def test_nonexistent_conflict_resolve_returns_404(self, api: httpx.Client, require_stack):
        r = api.post(f"/review/conflicts/{uuid.uuid4()}/resolve", json={
            "resolution": "both_valid",
            "note": "test",
            "reviewer": "test",
        }, timeout=10)
        assert r.status_code in (400, 404), (
            f"Resolving a nonexistent conflict returned {r.status_code} — expected 404"
        )

    def test_nonexistent_report_export_returns_404(self, api: httpx.Client, require_stack):
        r = api.get(f"/reports/{uuid.uuid4()}/export?format=pdf", timeout=10)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 7. Invalid request bodies → 422 validation errors
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestRequestValidation:
    def test_search_empty_query_returns_422(self, api: httpx.Client, require_stack):
        r = api.post("/search", json={"query": ""}, timeout=10)
        assert r.status_code == 422

    def test_analytics_compare_missing_entities_returns_422(
        self, api: httpx.Client, require_stack
    ):
        r = api.post("/analytics/compare", json={
            "metric": "coal_production",
            "period_start_year": 2020,
            "period_end_year": 2023,
            # entity_ids missing
        }, timeout=10)
        assert r.status_code == 422

    def test_conflict_resolve_invalid_resolution_returns_400(
        self, api: httpx.Client, require_stack
    ):
        """POST with an invalid resolution value must return 400."""
        # Find any conflict ID (even resolved one is fine for this test)
        r = api.get("/conflicts?page_size=1", timeout=15)
        conflicts = r.json().get("items", [])
        if not conflicts:
            pytest.skip("No conflicts in DB")

        cid = conflicts[0]["id"]
        r2 = api.post(f"/review/conflicts/{cid}/resolve", json={
            "resolution": "invalid_value_xyz",
            "note": "test",
            "reviewer": "test",
        }, timeout=10)
        assert r2.status_code in (400, 422), (
            f"Invalid resolution value returned {r2.status_code}, expected 400/422"
        )

    def test_report_generate_invalid_dates_returns_422(self, api: httpx.Client, require_stack):
        r = api.post("/reports/generate", json={
            "period_start": "not-a-date",
            "period_end": "also-not-a-date",
        }, timeout=10)
        assert r.status_code == 422

    def test_double_resolve_same_conflict_returns_400(self, api: httpx.Client, require_stack):
        """Resolving an already-resolved conflict must return 400."""
        r = api.get("/conflicts?page_size=50", timeout=15)
        resolved = [c for c in r.json().get("items", []) if c.get("status") == "resolved"]
        if not resolved:
            pytest.skip("No resolved conflicts to test double-resolve guard")

        cid = resolved[0]["id"]
        r2 = api.post(f"/review/conflicts/{cid}/resolve", json={
            "resolution": "both_valid",
            "note": "Attempting second resolve",
            "reviewer": "test",
        }, timeout=10)
        assert r2.status_code == 400, (
            f"Double-resolving a conflict returned {r2.status_code}, expected 400. "
            f"The system must refuse to overwrite an already-resolved conflict."
        )
        assert "already resolved" in r2.json().get("detail", "").lower(), (
            "Error message for double-resolve does not include 'already resolved'"
        )
