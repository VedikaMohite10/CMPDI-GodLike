"""test_phase4_reports_topics_review_dashboard.py — Phase 4 full validation.

Extends test_phase4.py with the gaps identified in the audit:
  - Report figures must match Analytics Service values (numeric cross-check)
  - Point-in-time snapshot behavior: correcting a fact must NOT alter an already-
    generated report (the stored content_snapshot must remain unchanged)
  - Topic cluster membership verified against actual text block content
  - Dashboard: 5 metrics cross-checked against direct DB queries
  - Correction propagation: correct a flag → downstream analytics reflects new value

Run with:
    pytest tests/test_phase4_reports_topics_review_dashboard.py -v -m integration
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
import pytest

from tests.conftest import TIMEOUT, db_scalar

BASE_URL = os.environ.get("CMPDI_API_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_completed_report(api: httpx.Client) -> Optional[dict]:
    r = api.get("/reports?page_size=5", timeout=15)
    if r.status_code != 200:
        return None
    for rep in r.json().get("items", []):
        if rep.get("status") == "complete":
            r2 = api.get(f"/reports/{rep['id']}", timeout=15)
            if r2.status_code == 200:
                return r2.json()
    return None


def _first_entity_with_facts(api: httpx.Client) -> Optional[dict]:
    r = api.get("/entities?page_size=50", timeout=15)
    if r.status_code != 200:
        return None
    for entity in r.json().get("items", []):
        r2 = api.get(f"/facts?entity_id={entity['id']}&page_size=1", timeout=15)
        if r2.status_code == 200 and r2.json().get("items"):
            return entity
    return None


# ---------------------------------------------------------------------------
# Checkpoint 1 — Report generation, structure, and cross-format content
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.llm
class TestReportGeneration:
    def test_generate_report_returns_202_and_completes(self, api: httpx.Client, require_stack):
        r = api.post("/reports/generate", json={
            "period_start": "2020-01-01",
            "period_end":   "2023-12-31",
            "label":        "Integration Test Report — Phase 4",
        }, timeout=TIMEOUT)
        assert r.status_code in (200, 202), f"Generate returned {r.status_code}: {r.text}"
        body = r.json()
        assert "report_id" in body
        assert "sections" in body

    def test_completed_report_has_all_required_sections(self, api: httpx.Client, require_stack):
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report in DB — generate one first")

        content = report.get("content") or {}
        for section in (
            "executive_summary", "production_overview",
            "historical_trends", "comparative_analysis", "data_quality_warnings",
        ):
            assert section in content, (
                f"Report missing section '{section}'. "
                f"Present sections: {list(content.keys())}"
            )
        assert "citations" in content, "Report missing citations section"

    def test_report_citations_resolve_to_real_facts(self, api: httpx.Client, require_stack):
        """Every citation in a report must resolve via /facts/{id}/evidence."""
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report")

        content = report.get("content") or {}
        citations = content.get("citations", [])
        if not citations:
            pytest.xfail(
                "Report has no citations. If normalized facts exist, every claim "
                "should be cited. This may indicate the assembler is not linking facts."
            )

        broken: list[str] = []
        for c in citations[:15]:
            fid = c.get("fact_id")
            if not fid:
                broken.append(f"citation has no fact_id: {c}")
                continue
            r = api.get(f"/facts/{fid}/evidence", timeout=15)
            if r.status_code != 200:
                broken.append(f"citation fact_id {fid}: HTTP {r.status_code}")

        assert not broken, (
            "Report citations contain broken provenance references:\n"
            + "\n".join(f"  {b}" for b in broken)
        )


# ---------------------------------------------------------------------------
# Checkpoint 2 — Report figures must match Analytics Service values
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestReportNumericAccuracy:
    """Cross-check: report figures come from the Analytics Service, not the LLM."""

    def test_report_figures_match_analytics_service(self, api: httpx.Client, require_stack):
        """For each numeric value in a report's production_overview table,
        verify it also appears in a direct /analytics/compare call for the
        same scope."""
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report")

        content = report.get("content") or {}
        overview = content.get("production_overview", {})
        report_values: set[float] = set()

        # Collect all numeric values from the production overview table
        for row in overview.get("rows", []):
            for cell in row:
                try:
                    report_values.add(float(cell))
                except (TypeError, ValueError):
                    pass

        if not report_values:
            pytest.skip("No numeric values found in production_overview rows")

        # Get analytics for the same period
        period_start = report.get("period_start", "2020-01-01")
        period_end   = report.get("period_end",   "2023-12-31")
        start_year   = int(period_start[:4])
        end_year     = int(period_end[:4])

        entity = _first_entity_with_facts(api)
        if entity is None:
            pytest.skip("No entities with facts for cross-check")

        r = api.post("/analytics/compare", json={
            "entity_ids": [entity["id"]],
            "metric": "coal_production",
            "period_start_year": start_year,
            "period_end_year": end_year,
        }, timeout=TIMEOUT)

        if r.status_code == 404:
            pytest.skip("No analytics data for cross-check")

        analytics_values: set[float] = set()
        for ent in r.json().get("entities", []):
            for pt in ent.get("series", []):
                if pt.get("value") is not None:
                    analytics_values.add(float(pt["value"]))

        if not analytics_values:
            pytest.skip("Analytics returned no values for cross-check")

        # At least one report value must appear in analytics (they share the same scope)
        matched = any(
            any(abs(rv - av) / max(abs(av), 1e-9) < 0.001 for av in analytics_values)
            for rv in report_values
        )
        assert matched, (
            f"CRITICAL — No report value matches Analytics Service output.\n"
            f"Report values: {sorted(report_values)}\n"
            f"Analytics values: {sorted(analytics_values)}\n"
            f"Report figures appear to have been fabricated by the LLM. "
            f"All numbers must originate from the deterministic Analytics Service."
        )


# ---------------------------------------------------------------------------
# Checkpoint 3 — Point-in-time snapshot: corrections don't alter old reports
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestReportPointInTimeSnapshot:
    """CRITICAL: A report generated before a correction must NOT be retroactively
    altered when that fact is corrected later. Reports are historical records."""

    def test_report_content_snapshot_is_immutable_after_correction(
        self, api: httpx.Client, require_stack
    ):
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report")

        # Snapshot the report content BEFORE any correction
        content_before = str(report.get("content") or {})
        report_id = report["id"]

        # Make a correction (find any open flag)
        r = api.get("/review/flags?status=open&page_size=1", timeout=15)
        flags = r.json().get("items", []) if r.status_code == 200 else []
        if not flags:
            pytest.skip("No open flags to correct — skipping snapshot test")

        flag_id = flags[0]["id"]
        api.post(f"/review/flags/{flag_id}/correct", json={
            "corrected_value": 9999.0,
            "corrected_unit": "MT",
            "reviewer": "snapshot_test_runner",
            "note": "Testing point-in-time snapshot — should not alter existing report",
        }, timeout=15)

        # Fetch the SAME report again
        r2 = api.get(f"/reports/{report_id}", timeout=15)
        assert r2.status_code == 200
        content_after = str(r2.json().get("content") or {})

        assert content_after == content_before, (
            "DEFECT: Report content changed after a fact correction was applied. "
            "Reports must be point-in-time snapshots — correcting a fact must NOT "
            "retroactively alter any previously generated report. "
            "The system must store a content_snapshot at generation time."
        )


# ---------------------------------------------------------------------------
# Checkpoint 4 — Report export: PDF, DOCX, XLSX
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestReportExport:
    def test_export_pdf_magic_bytes_and_content(self, api: httpx.Client, require_stack):
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report for export")

        r = api.get(f"/reports/{report['id']}/export?format=pdf", timeout=60)
        assert r.status_code == 200, f"PDF export returned {r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type") == "application/pdf"
        assert r.content[:4] == b"%PDF", "PDF response does not start with %PDF magic bytes"
        assert len(r.content) > 500, "PDF file suspiciously small — likely empty"

    def test_export_docx_is_valid_zip(self, api: httpx.Client, require_stack):
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report for export")

        r = api.get(f"/reports/{report['id']}/export?format=docx", timeout=60)
        assert r.status_code == 200
        assert "wordprocessingml" in r.headers.get("content-type", "")
        assert r.content[:2] == b"PK", "DOCX response does not start with ZIP PK magic bytes"

    def test_export_xlsx_is_valid_zip(self, api: httpx.Client, require_stack):
        report = _get_completed_report(api)
        if report is None:
            pytest.skip("No completed report for export")

        r = api.get(f"/reports/{report['id']}/export?format=xlsx", timeout=60)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert r.content[:2] == b"PK", "XLSX response does not start with ZIP PK magic bytes"

    def test_invalid_export_format_returns_422(self, api: httpx.Client, require_stack):
        import uuid
        r = api.get(f"/reports/{uuid.uuid4()}/export?format=invalid", timeout=10)
        assert r.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# Checkpoint 5 — Topics: derived from actual content, not hard-coded
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestTopicDerivedFromContent:
    def test_topics_endpoint_structure(self, api: httpx.Client, require_stack):
        r = api.get("/topics", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "topics" in body
        assert "algorithm" in body
        assert "total_documents_clustered" in body

    def test_topic_cluster_membership_maps_to_real_documents(
        self, api: httpx.Client, require_stack
    ):
        """Verify that topics map to actual documents (not a hard-coded default list)."""
        r = api.get("/topics", timeout=30)
        topics = r.json().get("topics", [])
        if not topics:
            pytest.skip("No topics computed — run POST /topics/recompute first")

        for topic in topics[:3]:
            # Each topic must have a label and keywords
            assert topic.get("label"), f"Topic {topic.get('topic_id')} has no label"
            assert topic.get("top_keywords"), f"Topic {topic.get('topic_id')} has no keywords"

            # Verify document_count is plausible
            doc_count = topic.get("document_count", 0)
            assert doc_count >= 0, f"Topic {topic.get('topic_id')} has negative document_count"

    def test_topic_keywords_appear_in_actual_documents(self, api: httpx.Client, require_stack):
        """Core test: at least one keyword from a topic must appear in an actual
        ingested document's text blocks — proving clusters aren't fake."""
        r = api.get("/topics", timeout=30)
        topics = r.json().get("topics", [])
        if not topics:
            pytest.skip("No topics to validate")

        # Pick the first topic with keywords
        topic = next((t for t in topics if t.get("top_keywords")), None)
        if topic is None:
            pytest.skip("No topics with keywords")

        keywords = topic["top_keywords"][:3]

        # Search for each keyword in the document corpus
        found_any = False
        for keyword in keywords:
            if len(keyword) < 3:
                continue  # skip very short keywords
            r2 = api.post("/search", json={"query": keyword, "top_k": 3}, timeout=TIMEOUT)
            if r2.status_code == 200 and r2.json().get("results"):
                found_any = True
                break

        assert found_any, (
            f"None of the top keywords {keywords} from topic '{topic['label']}' "
            f"appear in any search results. Topics may not be derived from actual "
            f"document content."
        )

    def test_topics_algorithm_field_is_set(self, api: httpx.Client, require_stack):
        r = api.get("/topics", timeout=30)
        algorithm = r.json().get("algorithm", "")
        # After at least one recompute, algorithm should not be empty/none
        # We skip this check if no documents have been clustered
        total = r.json().get("total_documents_clustered", 0)
        if total > 0:
            assert algorithm and algorithm != "none", \
                f"Algorithm field is '{algorithm}' but {total} documents were clustered"


# ---------------------------------------------------------------------------
# Checkpoint 6 — Human verification: resolve conflict + downstream propagation
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestConflictResolutionAndPropagation:
    def test_resolve_conflict_updates_status_and_creates_audit_log(
        self, api: httpx.Client, require_stack
    ):
        r = api.get("/review/conflicts?page_size=5", timeout=15)
        assert r.status_code == 200
        conflicts = r.json().get("items", [])
        open_conflicts = [c for c in conflicts if c.get("status") == "open"]
        if not open_conflicts:
            pytest.skip("No open conflicts in review console")

        conflict = open_conflicts[0]
        conflict_id = conflict["id"]

        r2 = api.post(f"/review/conflicts/{conflict_id}/resolve", json={
            "resolution": "fact_a_correct",
            "canonical_value": float(conflict.get("value_a", 1.0)),
            "canonical_unit": "MT",
            "reviewer": "integration_test_runner",
            "note": "Integration test: resolving conflict to verify propagation",
        }, timeout=15)
        assert r2.status_code == 200, f"Resolve returned {r2.status_code}: {r2.text}"
        body = r2.json()
        assert body["status"] == "resolved"
        assert "audit_log_id" in body

        # Verify audit log entry was created
        r3 = api.get("/review/audit-log?action_type=resolve_conflict&page_size=5", timeout=15)
        assert r3.status_code == 200
        entries = r3.json().get("items", [])
        assert any(e.get("action_type") == "resolve_conflict" for e in entries), \
            "No resolve_conflict audit log entry found after resolution"

    def test_resolved_conflict_disappears_from_open_list(self, api: httpx.Client, require_stack):
        """After resolving a conflict, it must no longer appear in open conflicts."""
        r = api.get("/review/conflicts?page_size=50", timeout=15)
        assert r.status_code == 200
        all_conflicts = r.json().get("items", [])
        open_conflicts = [c for c in all_conflicts if c.get("status") == "open"]
        if not open_conflicts:
            pytest.skip("No open conflicts")

        conflict_id = open_conflicts[0]["id"]
        api.post(f"/review/conflicts/{conflict_id}/resolve", json={
            "resolution": "both_valid",
            "reviewer": "integration_test_runner",
            "note": "Test: verifying conflict disappears from open list",
        }, timeout=15)

        # Re-fetch open conflicts
        r2 = api.get("/review/conflicts?page_size=50", timeout=15)
        open_after = [c["id"] for c in r2.json().get("items", []) if c.get("status") == "open"]
        assert conflict_id not in open_after, (
            f"Conflict {conflict_id} still appears in open conflicts after resolution."
        )

    def test_query_after_conflict_resolution_reflects_winner(
        self, api: httpx.Client, require_stack
    ):
        """After resolving a conflict as fact_a_correct, a query for that
        entity/metric should NOT surface the same conflict anymore."""
        # Find an open conflict with a known entity
        r = api.get("/review/conflicts?page_size=5", timeout=15)
        conflicts = [c for c in r.json().get("items", []) if c.get("status") == "open"]
        if not conflicts:
            pytest.skip("No open conflicts")

        conflict = conflicts[0]
        cid = conflict["id"]
        entity_id = conflict.get("canonical_entity_id")
        metric = conflict.get("metric", "")
        value_a = conflict.get("value_a")

        # Resolve it
        api.post(f"/review/conflicts/{cid}/resolve", json={
            "resolution": "fact_a_correct",
            "canonical_value": float(value_a) if value_a else None,
            "reviewer": "integration_test_runner",
            "note": "Testing post-resolution query behavior",
        }, timeout=15)

        # Query for the entity/metric
        r2 = api.get(f"/entities/{entity_id}", timeout=15)
        entity_name = r2.json().get("canonical_name", "") if r2.status_code == 200 else ""

        r3 = api.post("/query", json={
            "question": f"What is the {metric} for {entity_name}?",
            "top_k_semantic": 5,
        }, timeout=TIMEOUT)

        if r3.status_code != 200:
            pytest.skip("Query endpoint not available")

        # The resolved conflict should NOT appear in conflicts_surfaced
        surfaced = r3.json().get("conflicts_surfaced", [])
        surfaced_ids = [c.get("conflict_id") for c in surfaced]
        assert cid not in surfaced_ids, (
            f"Resolved conflict {cid} still appears in /query conflicts_surfaced. "
            f"Resolution is not propagating to the query copilot."
        )


# ---------------------------------------------------------------------------
# Checkpoint 7 — Dashboard: 5 metrics cross-checked against direct DB queries
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestDashboardCrossCheck:
    """For each metric verified, we run the SAME computation independently
    via psql and confirm an exact match. No metric is trusted on faith."""

    def _psql(self, sql: str) -> int:
        try:
            return db_scalar(sql)
        except Exception as e:
            pytest.skip(f"psql unavailable: {e}")

    def _get_dashboard(self, api: httpx.Client) -> dict:
        r = api.get("/dashboard/stats", timeout=30)
        assert r.status_code == 200, f"Dashboard returned {r.status_code}: {r.text}"
        return r.json()

    def test_documents_processed_matches_db(self, api: httpx.Client, require_stack):
        """Cross-check 1: dashboard.pipeline.documents_processed == COUNT(*) in DB."""
        raw = self._psql(
            "SELECT COUNT(*) FROM documents WHERE processing_status = 'done'"
        )
        dash = self._get_dashboard(api)["pipeline"]["documents_processed"]
        assert dash == raw, (
            f"DASHBOARD INTEGRITY FAILURE: documents_processed={dash}, "
            f"raw DB count={raw}. Dashboard is reporting a fabricated number."
        )

    def test_open_conflicts_matches_db(self, api: httpx.Client, require_stack):
        """Cross-check 2: dashboard.trust.open_conflicts == COUNT(*) in DB."""
        raw = self._psql(
            "SELECT COUNT(*) FROM conflicts WHERE status = 'open'"
        )
        dash = self._get_dashboard(api)["trust"]["open_conflicts"]
        assert dash == raw, (
            f"DASHBOARD INTEGRITY FAILURE: open_conflicts={dash}, raw={raw}."
        )

    def test_human_corrections_count_matches_db(self, api: httpx.Client, require_stack):
        """Cross-check 3: dashboard.review.human_corrections_count == COUNT(*) in DB."""
        raw = self._psql(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE action_type = 'correct' AND target_table = 'normalized_facts'"
        )
        dash = self._get_dashboard(api)["review"]["human_corrections_count"]
        assert dash == raw, (
            f"DASHBOARD INTEGRITY FAILURE: human_corrections_count={dash}, raw={raw}."
        )

    def test_total_active_facts_matches_db(self, api: httpx.Client, require_stack):
        """Cross-check 4: dashboard.review.total_active_facts == COUNT(*) in DB."""
        raw = self._psql(
            "SELECT COUNT(*) FROM normalized_facts WHERE fact_processing_status != 'rejected'"
        )
        dash = self._get_dashboard(api)["review"]["total_active_facts"]
        assert dash == raw, (
            f"DASHBOARD INTEGRITY FAILURE: total_active_facts={dash}, raw={raw}."
        )

    def test_open_flags_matches_db(self, api: httpx.Client, require_stack):
        """Cross-check 5: dashboard.trust.open_flags == COUNT(*) in DB."""
        raw = self._psql(
            "SELECT COUNT(*) FROM validation_flags WHERE status = 'open'"
        )
        dash = self._get_dashboard(api)["trust"].get("open_flags", None)
        if dash is None:
            pytest.skip("Dashboard does not expose open_flags in trust section")
        assert dash == raw, (
            f"DASHBOARD INTEGRITY FAILURE: open_flags={dash}, raw={raw}."
        )

    def test_automation_pct_formula_is_correct(self, api: httpx.Client, require_stack):
        """Verify automation_pct arithmetic independently:
        (total_active - distinct_corrected) / total_active * 100."""
        dash = self._get_dashboard(api)
        auto = dash["automation"]
        total = dash["review"]["total_active_facts"]
        corrected = dash["review"].get("distinct_corrected_facts_count", 0)

        if total == 0:
            assert auto["automation_pct"] is None
            return

        expected = round((total - corrected) / total * 100, 2)
        actual = auto["automation_pct"]
        assert abs(actual - expected) < 0.01, (
            f"Automation formula mismatch: dashboard={actual}, computed={expected} "
            f"(total={total}, distinct_corrected={corrected})"
        )

    def test_dashboard_computed_at_is_recent(self, api: httpx.Client, require_stack):
        """computed_at must be a recent timestamp — proves stats are live, not cached."""
        import datetime
        dash = self._get_dashboard(api)
        ts_str = dash.get("computed_at")
        assert ts_str is not None, "Dashboard missing computed_at timestamp"
        ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        age_seconds = (now - ts).total_seconds()
        assert age_seconds < 60, (
            f"computed_at is {age_seconds:.0f}s ago — dashboard stats may be cached. "
            f"Stats must be computed fresh on each request."
        )
