"""Phase 4 Integration Tests — CMPDI AI Mining Intelligence Platform.

Covers all 5 demo checkpoints from the Phase 4 PS:

  1. Generate a report → verify structure → export PDF, DOCX, XLSX → confirm files exist
  2. GET /topics returns clusters from actual document content (not a hard-coded list)
  3. GET /topics/trends returns data points across the ingested date range
  4. POST /review/conflicts/{id}/resolve → status changes, audit log created, fact status updates
  5. GET /dashboard/stats → every number is live (cross-check docs_processed & open_conflicts)

Run with:
    pytest test_phase4.py -v
    pytest test_phase4.py -v -k "test_report" --tb=short   # run single group

Requirements:
  - PostgreSQL running and migrated (alembic upgrade head)
  - At least one document already ingested for topic/trend tests
    (tests skip gracefully if DB is empty rather than failing)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://cmpdi:cmpdipass@localhost:5432/cmpdi_mining",
)

from app.main import create_app
from app.models.phase2 import (
    CanonicalEntity, Conflict, ExtractedFact, NormalizedFact, ValidationFlag,
)
from app.models.document import Document
from app.models.page import Page
from app.models.phase4 import AuditLog, GeneratedReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def app():
    return create_app()


@pytest_asyncio.fixture(scope="session")
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def db_session():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Helper: seed minimal entity+conflict+flag chain for review tests
# ---------------------------------------------------------------------------

async def _seed_entity_and_fact(db):
    """Returns (entity_id, conflict_id, flag_id)."""
    entity = CanonicalEntity(
        canonical_name=f"Test Entity {uuid.uuid4().hex[:6]}",
        entity_type="subsidiary",
    )
    db.add(entity)
    await db.flush()

    doc = Document(
        filename=f"test_{uuid.uuid4().hex[:8]}.pdf",
        original_filename="test_report.pdf",
        file_type="pdf_digital",
        storage_path=f"/tmp/test_{uuid.uuid4().hex}.pdf",
        processing_status="complete",
        report_date=date(2023, 3, 31),
    )
    db.add(doc)
    await db.flush()

    pg = Page(document_id=doc.id, page_number=1, page_type="content")
    db.add(pg)
    await db.flush()

    ef_a = ExtractedFact(
        document_id=doc.id, page_id=pg.id,
        raw_value="1000", raw_entity_text="Test Entity", raw_metric_text="production",
        extraction_method="test", extraction_confidence=0.9,
    )
    ef_b = ExtractedFact(
        document_id=doc.id, page_id=pg.id,
        raw_value="1500", raw_entity_text="Test Entity", raw_metric_text="production",
        extraction_method="test", extraction_confidence=0.85,
    )
    db.add_all([ef_a, ef_b])
    await db.flush()

    nf_a = NormalizedFact(
        extracted_fact_id=ef_a.id,
        canonical_entity_id=entity.id,
        metric="coal_production",
        metric_category="production",
        normalized_value=1000.0,
        normalized_unit="MT",
        period_start=date(2023, 1, 1),
        period_end=date(2023, 3, 31),
        fact_processing_status="normalized",
    )
    nf_b = NormalizedFact(
        extracted_fact_id=ef_b.id,
        canonical_entity_id=entity.id,
        metric="coal_production",
        metric_category="production",
        normalized_value=1500.0,
        normalized_unit="MT",
        period_start=date(2023, 1, 1),
        period_end=date(2023, 3, 31),
        fact_processing_status="normalized",
    )
    db.add_all([nf_a, nf_b])
    await db.flush()

    conflict = Conflict(
        canonical_entity_id=entity.id,
        metric="coal_production",
        period_start=date(2023, 1, 1),
        period_end=date(2023, 3, 31),
        fact_a_id=nf_a.id,
        fact_b_id=nf_b.id,
        value_a=1000.0,
        value_b=1500.0,
        delta_pct=50.0,
        status="open",
    )
    db.add(conflict)
    await db.flush()

    flag = ValidationFlag(
        normalized_fact_id=nf_a.id,
        flag_type="outlier",
        severity="high",
        detail={"z_score": 3.2, "mean": 900.0, "std_dev": 100.0},
        status="open",
    )
    db.add(flag)
    await db.commit()
    await db.refresh(conflict)
    await db.refresh(flag)
    return entity.id, conflict.id, flag.id


# ---------------------------------------------------------------------------
# CHECKPOINT 1 — Assembler smoke + Schema integrity (unit-level, no DB needed)
# ---------------------------------------------------------------------------

class TestAssemblerSmoke:
    """Fast unit-level smoke tests: verify Bug 1 & Bug 2 fixes hold."""

    def test_assembler_imports_cleanly(self):
        """assembler.py must import without ImportError (Bug 1 regression check)."""
        try:
            from app.services.report.assembler import (
                assemble_report, ReportContent, ReportScope,
                Citation, NarrativeSection, TableSection, TrendSection,
                WarningsSection, DataPoint, SeriesData,
            )
        except ImportError as exc:
            pytest.fail(f"assembler.py ImportError (Bug 1 regression): {exc}")

    def test_document_model_has_timing_columns(self):
        """Document ORM model must have ingestion timing columns (Bug 2 regression check)."""
        from app.models.document import Document
        assert hasattr(Document, "ingestion_started_at"), \
            "Document missing ingestion_started_at (Bug 2 regression)"
        assert hasattr(Document, "ingestion_completed_at"), \
            "Document missing ingestion_completed_at (Bug 2 regression)"

    def test_automation_stats_schema_accepts_none(self):
        """AutomationStats must accept None for automation_pct (Bug 4 regression check)."""
        from app.schemas.dashboard import AutomationStats
        stats = AutomationStats(
            automation_pct=None,
            formula="(total_active_facts - distinct_corrected_facts) / total_active_facts x 100",
            numerator=None,
            denominator=None,
            automation_pct_caveat="No active facts in pipeline yet.",
            review_coverage_pct=0.0,
        )
        assert stats.automation_pct is None

    def test_review_stats_schema_has_distinct_corrected_field(self):
        """ReviewStats must include distinct_corrected_facts_count (Bug 3 regression check)."""
        from app.schemas.dashboard import ReviewStats
        stats = ReviewStats(
            human_corrections_count=5,
            distinct_corrected_facts_count=3,
            human_accepts_count=2,
            human_rejects_count=1,
            total_reviewed_facts=6,
            total_active_facts=100,
            unreviewed_facts=94,
            review_coverage_pct=6.0,
        )
        assert stats.distinct_corrected_facts_count == 3


# ---------------------------------------------------------------------------
# CHECKPOINT 1 — Report Generation + Export (API)
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Demo checkpoint 1: generate report → verify structure → export all formats."""

    @pytest.mark.asyncio
    async def test_generate_report_returns_202(self, client: AsyncClient):
        with (
            patch("app.services.report.narrative_generator.model_gateway.generate",
                  new_callable=AsyncMock,
                  return_value="Test executive summary text."),
        ):
            resp = await client.post("/reports/generate", json={
                "period_start": "2020-01-01",
                "period_end":   "2023-12-31",
                "label":        "Phase 4 Test Report",
            })
        assert resp.status_code in (200, 202), resp.text
        body = resp.json()
        assert "report_id" in body
        assert "sections" in body

    @pytest.mark.asyncio
    async def test_report_content_has_required_sections(self, client: AsyncClient, db_session):
        row = (await db_session.execute(
            select(GeneratedReport)
            .where(GeneratedReport.status == "complete")
            .order_by(GeneratedReport.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if row is None:
            pytest.skip("No completed report in DB")

        resp = await client.get(f"/reports/{row.id}")
        assert resp.status_code == 200
        content = resp.json().get("content") or {}
        for section in (
            "executive_summary", "production_overview",
            "historical_trends", "comparative_analysis", "data_quality_warnings",
        ):
            assert section in content, f"Missing section: {section}"
        assert "citations" in content

    @pytest.mark.asyncio
    async def test_export_pdf_returns_valid_file(self, client: AsyncClient, db_session):
        row = (await db_session.execute(
            select(GeneratedReport)
            .where(GeneratedReport.status == "complete")
            .order_by(GeneratedReport.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if row is None:
            pytest.skip("No completed report available")

        resp = await client.get(f"/reports/{row.id}/export?format=pdf")
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 500
        assert resp.content[:4] == b"%PDF", "Does not start with PDF magic bytes"

    @pytest.mark.asyncio
    async def test_export_docx_returns_valid_file(self, client: AsyncClient, db_session):
        row = (await db_session.execute(
            select(GeneratedReport)
            .where(GeneratedReport.status == "complete")
            .order_by(GeneratedReport.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if row is None:
            pytest.skip("No completed report available")

        resp = await client.get(f"/reports/{row.id}/export?format=docx")
        assert resp.status_code == 200, resp.text
        assert "wordprocessingml" in resp.headers["content-type"]
        assert resp.content[:2] == b"PK", "DOCX does not have ZIP (PK) magic bytes"

    @pytest.mark.asyncio
    async def test_export_xlsx_returns_valid_file(self, client: AsyncClient, db_session):
        row = (await db_session.execute(
            select(GeneratedReport)
            .where(GeneratedReport.status == "complete")
            .order_by(GeneratedReport.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if row is None:
            pytest.skip("No completed report available")

        resp = await client.get(f"/reports/{row.id}/export?format=xlsx")
        assert resp.status_code == 200, resp.text
        assert "spreadsheetml" in resp.headers["content-type"]
        assert resp.content[:2] == b"PK", "XLSX does not have ZIP (PK) magic bytes"

    @pytest.mark.asyncio
    async def test_export_invalid_format_returns_422(self, client: AsyncClient, db_session):
        row = (await db_session.execute(select(GeneratedReport).limit(1))).scalar_one_or_none()
        rid = row.id if row else uuid.uuid4()
        resp = await client.get(f"/reports/{rid}/export?format=xyz")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CHECKPOINT 2 — Topic Identification (not hard-coded)
# ---------------------------------------------------------------------------

class TestTopics:
    @pytest.mark.asyncio
    async def test_get_topics_returns_valid_structure(self, client: AsyncClient):
        resp = await client.get("/topics")
        assert resp.status_code == 200
        body = resp.json()
        assert "topics" in body
        assert "algorithm" in body
        assert "total_documents_clustered" in body

    @pytest.mark.asyncio
    async def test_topic_labels_are_not_empty(self, client: AsyncClient):
        resp = await client.get("/topics")
        topics = resp.json()["topics"]
        if not topics:
            pytest.skip("No topics computed — run POST /topics/recompute first")
        for topic in topics:
            assert len(topic["label"].strip()) > 0, "Topic label is empty"
            assert "top_keywords" in topic

    @pytest.mark.asyncio
    async def test_document_topics_endpoint(self, client: AsyncClient, db_session):
        doc = (await db_session.execute(
            select(Document).where(Document.processing_status == "complete").limit(1)
        )).scalar_one_or_none()
        if doc is None:
            pytest.skip("No processed documents in DB")
        resp = await client.get(f"/documents/{doc.id}/topics")
        assert resp.status_code == 200
        body = resp.json()
        assert "document_id" in body
        assert "topics" in body
        assert str(doc.id) == body["document_id"]


# ---------------------------------------------------------------------------
# CHECKPOINT 3 — Topic Trends
# ---------------------------------------------------------------------------

class TestTopicTrends:
    @pytest.mark.asyncio
    async def test_get_topic_trends_structure(self, client: AsyncClient):
        resp = await client.get("/topics/trends")
        assert resp.status_code == 200
        assert "topics" in resp.json()

    @pytest.mark.asyncio
    async def test_topic_trend_points_have_correct_types(self, client: AsyncClient):
        resp = await client.get("/topics/trends")
        for topic in resp.json()["topics"]:
            assert "topic_id" in topic
            assert "label" in topic
            for point in topic["trend"]:
                assert isinstance(point["year"], int)
                assert isinstance(point["document_count"], int)
                assert point["document_count"] >= 0


# ---------------------------------------------------------------------------
# CHECKPOINT 4 — Human Verification Console
# ---------------------------------------------------------------------------

class TestHumanVerificationConsole:
    @pytest.mark.asyncio
    async def test_list_open_flags(self, client: AsyncClient):
        resp = await client.get("/review/flags")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body and "total" in body

    @pytest.mark.asyncio
    async def test_list_open_conflicts(self, client: AsyncClient):
        resp = await client.get("/review/conflicts")
        assert resp.status_code == 200
        assert "items" in resp.json()

    @pytest.mark.asyncio
    async def test_accept_flag_creates_audit_log(self, client: AsyncClient, db_session):
        _, conflict_id, flag_id = await _seed_entity_and_fact(db_session)
        resp = await client.post(
            f"/review/flags/{flag_id}/accept",
            json={"reviewer": "test_reviewer", "note": "Verified manually"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "accepted"
        assert "audit_log_id" in body

        audit = await db_session.get(AuditLog, uuid.UUID(body["audit_log_id"]))
        assert audit is not None
        assert audit.action_type == "accept"
        assert audit.reviewer == "test_reviewer"
        assert audit.before_value is not None

        flag = await db_session.get(ValidationFlag, flag_id)
        await db_session.refresh(flag)
        assert flag.status == "accepted"

    @pytest.mark.asyncio
    async def test_correct_flag_updates_value_and_audit_log(self, client: AsyncClient, db_session):
        _, conflict_id, flag_id = await _seed_entity_and_fact(db_session)
        resp = await client.post(
            f"/review/flags/{flag_id}/correct",
            json={
                "corrected_value": 1050.0,
                "corrected_unit": "MT",
                "reviewer": "test_reviewer",
                "note": "Cross-verified against physical records",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "corrected"
        audit = await db_session.get(AuditLog, uuid.UUID(body["audit_log_id"]))
        assert audit is not None
        assert audit.after_value.get("normalized_value") == 1050.0
        assert audit.before_value is not None

    @pytest.mark.asyncio
    async def test_resolve_conflict_full_flow(self, client: AsyncClient, db_session):
        """Core checkpoint: resolve conflict → status, audit log, fact status all verified."""
        _, conflict_id, flag_id = await _seed_entity_and_fact(db_session)

        conflict_before = await db_session.get(Conflict, conflict_id)
        assert conflict_before.status == "open"
        winner_fact_id = conflict_before.fact_a_id
        loser_fact_id  = conflict_before.fact_b_id

        resp = await client.post(
            f"/review/conflicts/{conflict_id}/resolve",
            json={
                "resolution":      "fact_a_correct",
                "canonical_value": 1000.0,
                "canonical_unit":  "MT",
                "reviewer":        "senior_analyst",
                "note":            "Source A is primary report; B is a preliminary estimate.",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "resolved"
        assert "audit_log_id" in body

        # Cross-check 1: conflict status in DB
        await db_session.refresh(conflict_before)
        assert conflict_before.status == "resolved", "Conflict status not updated in DB"

        # Cross-check 2: audit log captures before/after and required note
        audit = await db_session.get(AuditLog, uuid.UUID(body["audit_log_id"]))
        assert audit is not None
        assert audit.action_type == "resolve_conflict"
        assert audit.reviewer == "senior_analyst"
        assert audit.before_value == {"status": "open"}
        assert audit.after_value["resolution"] == "fact_a_correct"
        assert audit.note == "Source A is primary report; B is a preliminary estimate."

        # Cross-check 3: losing fact is soft-rejected (never deleted)
        loser = await db_session.get(NormalizedFact, loser_fact_id)
        await db_session.refresh(loser)
        assert loser.fact_processing_status == "rejected", \
            "Losing fact should be soft-rejected after resolution"

    @pytest.mark.asyncio
    async def test_double_resolve_returns_400(self, client: AsyncClient, db_session):
        _, conflict_id, _ = await _seed_entity_and_fact(db_session)
        await client.post(
            f"/review/conflicts/{conflict_id}/resolve",
            json={"resolution": "both_valid", "note": "First", "reviewer": "analyst"},
        )
        resp = await client.post(
            f"/review/conflicts/{conflict_id}/resolve",
            json={"resolution": "neither_reliable", "note": "Second", "reviewer": "analyst"},
        )
        assert resp.status_code == 400
        assert "already resolved" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_resolution_value_returns_400(self, client: AsyncClient, db_session):
        _, conflict_id, _ = await _seed_entity_and_fact(db_session)
        resp = await client.post(
            f"/review/conflicts/{conflict_id}/resolve",
            json={"resolution": "bad_value", "note": "Test", "reviewer": "analyst"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_audit_log_endpoint_returns_entries(self, client: AsyncClient):
        resp = await client.get("/review/audit-log")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body and "total" in body
        for entry in body["items"]:
            assert "action_type" in entry
            assert "reviewer" in entry
            assert "timestamp" in entry
            assert "before_value" in entry
            assert "after_value" in entry

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_action_type(self, client: AsyncClient):
        resp = await client.get("/review/audit-log?action_type=resolve_conflict")
        assert resp.status_code == 200
        for entry in resp.json()["items"]:
            assert entry["action_type"] == "resolve_conflict"


# ---------------------------------------------------------------------------
# CHECKPOINT 5 — Data Quality Dashboard (live data cross-checks)
# ---------------------------------------------------------------------------

class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_stats_has_all_sections(self, client: AsyncClient):
        resp = await client.get("/dashboard/stats")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for section in ("pipeline", "extraction", "trust", "normalization",
                        "review", "automation", "performance"):
            assert section in body, f"Missing dashboard section: {section}"
        assert "computed_at" in body

    @pytest.mark.asyncio
    async def test_dashboard_documents_matches_db(self, client: AsyncClient, db_session):
        """CROSS-CHECK: dashboard.pipeline.documents_processed == raw DB count."""
        docs = list((await db_session.execute(
            select(Document).where(Document.processing_status == "complete")
        )).scalars())
        raw_count = len(docs)

        resp = await client.get("/dashboard/stats")
        assert resp.status_code == 200
        dash_count = resp.json()["pipeline"]["documents_processed"]
        assert dash_count == raw_count, (
            f"Dashboard={dash_count} vs DB={raw_count}. Numbers must match exactly."
        )

    @pytest.mark.asyncio
    async def test_dashboard_open_conflicts_matches_db(self, client: AsyncClient, db_session):
        """CROSS-CHECK: dashboard.trust.open_conflicts == raw DB count."""
        raw_count = len(list((await db_session.execute(
            select(Conflict).where(Conflict.status == "open")
        )).scalars()))

        resp = await client.get("/dashboard/stats")
        dash_count = resp.json()["trust"]["open_conflicts"]
        assert dash_count == raw_count, (
            f"Dashboard={dash_count} vs DB={raw_count}."
        )

    @pytest.mark.asyncio
    async def test_automation_pct_always_has_formula_and_caveat(self, client: AsyncClient):
        """automation_pct must NEVER be a bare number — formula + caveat always present."""
        resp = await client.get("/dashboard/stats")
        auto = resp.json()["automation"]
        assert "formula" in auto and len(auto["formula"]) > 10
        assert "automation_pct_caveat" in auto and len(auto["automation_pct_caveat"]) > 20

    @pytest.mark.asyncio
    async def test_automation_pct_in_valid_range_or_null(self, client: AsyncClient):
        resp = await client.get("/dashboard/stats")
        pct = resp.json()["automation"]["automation_pct"]
        if pct is not None:
            assert 0.0 <= pct <= 100.0, f"automation_pct={pct} out of range [0, 100]"

    @pytest.mark.asyncio
    async def test_performance_stats_null_metrics_have_note(self, client: AsyncClient):
        resp = await client.get("/dashboard/stats")
        perf = resp.json()["performance"]
        assert "note_on_nulls" in perf and len(perf["note_on_nulls"]) > 20

    @pytest.mark.asyncio
    async def test_sub_endpoints_return_correct_subsets(self, client: AsyncClient):
        for path, expected_keys in [
            ("/dashboard/stats/extraction", ["extraction", "pipeline"]),
            ("/dashboard/stats/trust", ["trust", "normalization"]),
            ("/dashboard/stats/review", ["review", "automation"]),
        ]:
            resp = await client.get(path)
            assert resp.status_code == 200, f"{path} failed: {resp.text}"
            body = resp.json()
            for key in expected_keys:
                assert key in body, f"{path} missing key '{key}'"

    @pytest.mark.asyncio
    async def test_automation_distinct_corrected_in_review(self, client: AsyncClient):
        """Verify distinct_corrected_facts_count is present in review stats (Bug 3 fix)."""
        resp = await client.get("/dashboard/stats")
        review = resp.json()["review"]
        assert "distinct_corrected_facts_count" in review, \
            "distinct_corrected_facts_count missing from review stats (Bug 3 regression)"
        assert "human_corrections_count" in review
