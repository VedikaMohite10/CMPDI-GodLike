"""test_components_unit.py — Fast, deterministic unit tests for all CMPDI platform modules.

Tests business logic, metric normalization, date parsing, heuristic extraction,
confidence scoring, schema validation, and FastAPI route registration without requiring
external servers (Ollama, PostgreSQL, or Qdrant).

Run with:
    python -m pytest tests/test_components_unit.py -v
"""
from __future__ import annotations

import datetime
from pathlib import Path
import pytest
from fastapi import FastAPI

ROOT_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Metric Registry & Unit Normalization
# ---------------------------------------------------------------------------
class TestMetricAndUnitNormalization:
    """Verifies domain dictionary, alias resolution, and unit conversion formulas."""

    def test_metric_resolution_aliases(self):
        from app.services.phase2.metric_registry import resolve_metric

        assert resolve_metric("Production (MT)") == "coal_production"
        assert resolve_metric("coal output") == "coal_production"
        assert resolve_metric("Raw Coal Production") == "coal_production"
        assert resolve_metric("OB Removal (MCM)") == "ob_removal"
        assert resolve_metric("Overburden Removal") == "ob_removal"
        assert resolve_metric("seam depth") == "seam_depth"
        assert resolve_metric("coal seam depth") == "seam_depth"
        assert resolve_metric("nonexistent_metric_foo_bar") is None

    def test_unit_resolution(self):
        from app.services.phase2.metric_registry import resolve_unit

        res_mt = resolve_unit("MT")
        assert res_mt is not None
        canonical, factor = res_mt
        assert canonical == "MT"
        assert factor == 1.0

        res_lt = resolve_unit("lakh tonnes")
        assert res_lt is not None
        canonical, factor = res_lt
        assert canonical == "MT"
        assert factor == 0.1

        res_mcm = resolve_unit("MCM")
        assert res_mcm is not None
        assert res_mcm[0] == "MCM"

    def test_unit_conversion_math(self):
        from app.services.phase2.unit_normalizer import normalize_unit

        # 10 Lakh Tonnes = 1.0 Million Tonnes (MT)
        norm_val, norm_unit, note, notes = normalize_unit("10.0", "lakh tonnes")
        assert norm_unit == "MT"
        assert pytest.approx(norm_val, rel=1e-3) == 1.0

        # Tonnes to MT (2,500,000 tonnes = 2.5 MT)
        norm_val, norm_unit, note, notes = normalize_unit("2500000", "tonnes")
        assert norm_unit == "MT"
        assert pytest.approx(norm_val, rel=1e-3) == 2.5


# ---------------------------------------------------------------------------
# 2. Date & Financial Year Normalization
# ---------------------------------------------------------------------------
class TestDateAndPeriodNormalization:
    """Verifies Indian Financial Year (April-March) and calendar date parsing."""

    def test_fy_string_parsing(self):
        from app.services.phase2.date_normalizer import parse_date

        # FY 2021-22 runs 2021-04-01 to 2022-03-31
        start, end, label, method = parse_date("FY 2021-22")
        assert start == datetime.date(2021, 4, 1)
        assert end == datetime.date(2022, 3, 31)
        assert method == "fy_pattern"

    def test_fy_shorthand(self):
        from app.services.phase2.date_normalizer import parse_date

        start, end, label, method = parse_date("2022-23")
        assert start == datetime.date(2022, 4, 1)
        assert end == datetime.date(2023, 3, 31)
        assert method == "fy_pattern"

    def test_calendar_year_parsing(self):
        from app.services.phase2.date_normalizer import parse_date

        start, end, label, method = parse_date("2023")
        assert start == datetime.date(2023, 1, 1)
        assert end == datetime.date(2023, 12, 31)
        assert method == "year_only"


# ---------------------------------------------------------------------------
# 3. Heuristic Document Extraction
# ---------------------------------------------------------------------------
class TestHeuristicTextExtraction:
    """Verifies regex and table pattern matching for offline fact extraction."""

    def test_extract_facts_from_report_sentence(self):
        from app.services.phase2.heuristic_text_extractor import extract_from_text

        sample_text = (
            "During the last financial year, raw coal production reached 52.5 MT, "
            "and OB removal was 41.2 MCM."
        )
        facts = extract_from_text(sample_text)
        assert len(facts) >= 1
        metrics = [f.get("raw_metric_text") for f in facts]
        assert "coal_production" in metrics or "ob_removal" in metrics

    def test_empty_and_noise_resilience(self):
        from app.services.phase2.heuristic_text_extractor import extract_from_text

        assert extract_from_text("") == []
        assert extract_from_text("The committee meeting adjourned at 5 PM on Monday.") == []


# ---------------------------------------------------------------------------
# 4. Confidence & Trust Calculation
# ---------------------------------------------------------------------------
class TestConfidenceScoring:
    """Verifies deterministic confidence and evidence scoring bounds."""

    def test_confidence_computation_bounds(self):
        from app.services.explainer import _compute_confidence

        high_conf = _compute_confidence(
            extraction_scores=[0.95, 0.90],
            cross_validation_scores=[1.0, 1.0],
            reasoning_type="document-supported",
            tasks_planned=2,
            tasks_with_results=2,
        )
        assert isinstance(high_conf, int)
        assert 0 <= high_conf <= 100
        assert high_conf > 70

        low_conf = _compute_confidence(
            extraction_scores=[0.30],
            cross_validation_scores=[0.30],
            reasoning_type="insufficient-evidence",
            tasks_planned=2,
            tasks_with_results=0,
        )
        assert 0 <= low_conf <= 100
        assert low_conf < high_conf


# ---------------------------------------------------------------------------
# 5. FastAPI App & Router Registration Integrity
# ---------------------------------------------------------------------------
class TestFastAPIApplicationIntegrity:
    """Ensures all API routes from Phase 1 through Phase 5 mount cleanly without import collisions."""

    def test_app_created_and_configured(self):
        from app.main import app
        assert isinstance(app, FastAPI)
        assert app.title is not None

    def test_required_endpoints_registered(self):
        from app.main import app

        paths = []
        for r in app.router.routes:
            if hasattr(r, "path") and r.path:
                paths.append(r.path)
            if hasattr(r, "original_router"):
                prefix = getattr(getattr(r, "include_context", None), "prefix", "") or ""
                for sr in r.original_router.routes:
                    if hasattr(sr, "path") and sr.path:
                        paths.append(prefix + sr.path)

        expected_routes = [
            "/health",
            "/docs",
            "/openapi.json",
            "/documents",
            "/search",
            "/facts",
            "/conflicts",
            "/query",
            "/analytics",
            "/reports",
            "/topics",
            "/review",
            "/dashboard",
            "/auth",
            "/parliamentary",
            "/map",
            "/forecast",
        ]
        for expected in expected_routes:
            assert any(p == expected or p.startswith(expected) for p in paths), (
                f"Missing expected route prefix in FastAPI app: '{expected}'"
            )


# ---------------------------------------------------------------------------
# 6. File & MIME Sniffing Logic
# ---------------------------------------------------------------------------
class TestFileSniffing:
    """Verifies MIME detection using magic bytes."""

    def test_pdf_magic_bytes_detection(self):
        import filetype
        fake_pdf = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj"
        kind = filetype.guess(fake_pdf)
        assert kind is not None
        assert kind.mime == "application/pdf"

    def test_png_magic_bytes_detection(self):
        import filetype
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        kind = filetype.guess(fake_png)
        assert kind is not None
        assert kind.mime == "image/png"
