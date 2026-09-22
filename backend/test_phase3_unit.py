"""Phase 3 — Unit tests (no DB, no Ollama, no Qdrant required).

Coverage:
  1. Confidence formula — known inputs → expected score
  2. Analytics math — YoY, CAGR, anomaly detection
  3. Insufficient-evidence enforcement at all 4 structural layers (mocked)
  4. ModelGateway JSON extraction + validation
  5. Intent-plan fallback on gateway failure
"""
import asyncio
import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test 1 — Confidence Formula
# ---------------------------------------------------------------------------

from app.services.explainer import _compute_confidence


class TestConfidenceFormula:
    """Validates the deterministic confidence scoring formula."""

    def test_perfect_score(self):
        """All signals at maximum → 100."""
        score = _compute_confidence(
            extraction_scores=[1.0, 1.0, 1.0],
            cross_validation_scores=[1.0, 1.0, 1.0],
            reasoning_type="document-supported",
            tasks_planned=2,
            tasks_with_results=2,
        )
        assert score == 100

    def test_insufficient_evidence_caps_reasoning(self):
        """insufficient-evidence gives reasoning_bonus=0.0 → score is lower."""
        full = _compute_confidence(
            extraction_scores=[1.0],
            cross_validation_scores=[1.0],
            reasoning_type="document-supported",
            tasks_planned=1,
            tasks_with_results=1,
        )
        insuff = _compute_confidence(
            extraction_scores=[1.0],
            cross_validation_scores=[1.0],
            reasoning_type="insufficient-evidence",
            tasks_planned=1,
            tasks_with_results=1,
        )
        assert insuff < full
        assert insuff == round((0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 0.0 + 0.15 * 1.0) * 100)

    def test_open_conflict_penalises_cross_validation(self):
        """Open-conflict facts get cv_score=0.3 → lower confidence than clean facts."""
        clean = _compute_confidence(
            extraction_scores=[0.9],
            cross_validation_scores=[1.0],
            reasoning_type="data-derived",
            tasks_planned=1,
            tasks_with_results=1,
        )
        conflicted = _compute_confidence(
            extraction_scores=[0.9],
            cross_validation_scores=[0.3],
            reasoning_type="data-derived",
            tasks_planned=1,
            tasks_with_results=1,
        )
        assert conflicted < clean

    def test_zero_coverage_brings_score_down(self):
        """zero tasks_with_results/tasks_planned → coverage_score=0."""
        full_cov = _compute_confidence(
            extraction_scores=[0.8],
            cross_validation_scores=[1.0],
            reasoning_type="document-supported",
            tasks_planned=2,
            tasks_with_results=2,
        )
        no_cov = _compute_confidence(
            extraction_scores=[0.8],
            cross_validation_scores=[1.0],
            reasoning_type="document-supported",
            tasks_planned=2,
            tasks_with_results=0,
        )
        assert no_cov < full_cov

    def test_known_calculation_from_design_doc(self):
        """Replicates the worked example from the implementation plan:
        ext=0.85, cv=1.0, reasoning=doc-supported, coverage=1.0 → 95.
        """
        score = _compute_confidence(
            extraction_scores=[0.85, 0.85, 0.85, 0.85],
            cross_validation_scores=[1.0, 1.0, 1.0, 1.0],
            reasoning_type="document-supported",
            tasks_planned=2,
            tasks_with_results=2,
        )
        # 0.35*0.85 + 0.30*1.0 + 0.20*1.0 + 0.15*1.0 = 0.2975+0.30+0.20+0.15 = 0.9475 → 95
        assert score == 95

    def test_score_clamped_0_to_100(self):
        """Score never goes below 0 or above 100."""
        low = _compute_confidence(
            extraction_scores=[0.0],
            cross_validation_scores=[0.0],
            reasoning_type="insufficient-evidence",
            tasks_planned=5,
            tasks_with_results=0,
        )
        assert 0 <= low <= 100

    def test_data_derived_between_doc_and_insuff(self):
        """data-derived confidence falls between document-supported and insufficient."""
        doc = _compute_confidence([0.8], [1.0], "document-supported", 1, 1)
        derived = _compute_confidence([0.8], [1.0], "data-derived", 1, 1)
        insuff = _compute_confidence([0.8], [1.0], "insufficient-evidence", 1, 1)
        assert insuff < derived < doc

    def test_no_facts_neutral_extraction(self):
        """Empty fact list → extraction_score defaults to 0.5."""
        score = _compute_confidence(
            extraction_scores=[],
            cross_validation_scores=[],
            reasoning_type="document-supported",
            tasks_planned=0,
            tasks_with_results=0,
        )
        # extraction=0.5, cv=1.0 (no conflicts), reasoning=1.0, coverage=0.0 (no facts for semantic)
        expected = round((0.35 * 0.5 + 0.30 * 1.0 + 0.20 * 1.0 + 0.15 * 0.0) * 100)
        assert score == expected


# ---------------------------------------------------------------------------
# Test 2 — Analytics Math
# ---------------------------------------------------------------------------

from app.services.analytics.analytics_service import (
    DataPoint,
    compute_cagr,
    compute_yoy,
    detect_anomalies_for_series,
)


def _dp(label: str, value: Optional[float], start: date, end: Optional[date] = None,
        fid: Optional[uuid.UUID] = None) -> DataPoint:
    return DataPoint(
        period_label=label,
        period_start=start,
        period_end=end or start,
        value=value,
        fact_id=fid or uuid.uuid4(),
    )


class TestYoYChange:
    def test_basic_yoy(self):
        pts = [
            _dp("FY21", 38.2, date(2020, 4, 1), date(2021, 3, 31)),
            _dp("FY22", 41.1, date(2021, 4, 1), date(2022, 3, 31)),
            _dp("FY23", 43.7, date(2022, 4, 1), date(2023, 3, 31)),
        ]
        changes = compute_yoy(pts)
        assert len(changes) == 2
        # FY21→FY22: (41.1-38.2)/38.2 * 100 = 7.59
        assert changes[0].from_period == "FY21"
        assert changes[0].to_period == "FY22"
        assert abs(changes[0].pct_change - 7.59) < 0.1

    def test_yoy_negative_change(self):
        pts = [
            _dp("FY21", 50.0, date(2020, 4, 1)),
            _dp("FY22", 45.0, date(2021, 4, 1)),
        ]
        changes = compute_yoy(pts)
        assert changes[0].pct_change < 0
        assert abs(changes[0].pct_change - (-10.0)) < 0.01

    def test_yoy_skips_none_values(self):
        pts = [
            _dp("FY20", None, date(2019, 4, 1)),
            _dp("FY21", 38.0, date(2020, 4, 1)),
            _dp("FY22", 41.0, date(2021, 4, 1)),
        ]
        changes = compute_yoy(pts)
        assert len(changes) == 1  # None point excluded

    def test_yoy_single_point_returns_empty(self):
        pts = [_dp("FY21", 38.0, date(2020, 4, 1))]
        assert compute_yoy(pts) == []

    def test_yoy_preserves_fact_ids(self):
        fid1, fid2 = uuid.uuid4(), uuid.uuid4()
        pts = [
            _dp("FY21", 38.0, date(2020, 4, 1), fid=fid1),
            _dp("FY22", 41.0, date(2021, 4, 1), fid=fid2),
        ]
        changes = compute_yoy(pts)
        assert fid1 in changes[0].fact_ids_used
        assert fid2 in changes[0].fact_ids_used


class TestCAGR:
    def test_basic_cagr(self):
        fid1, fid2 = uuid.uuid4(), uuid.uuid4()
        pts = [
            _dp("FY18", 30.0, date(2017, 4, 1), fid=fid1),
            _dp("FY23", 43.7, date(2022, 4, 1), fid=fid2),
        ]
        cagr, ids = compute_cagr(pts, [fid1, fid2])
        # (43.7/30.0)^(1/5) - 1 ≈ 7.8%
        assert cagr is not None
        assert abs(cagr - 7.8) < 0.3

    def test_cagr_requires_two_points(self):
        pts = [_dp("FY21", 38.0, date(2020, 4, 1))]
        cagr, ids = compute_cagr(pts, [])
        assert cagr is None
        assert ids == []

    def test_cagr_requires_positive_values(self):
        pts = [
            _dp("FY21", 0.0, date(2020, 4, 1)),
            _dp("FY22", 41.0, date(2021, 4, 1)),
        ]
        cagr, _ = compute_cagr(pts, [])
        assert cagr is None

    def test_cagr_same_year_returns_none(self):
        """Zero years between start and end → CAGR undefined."""
        pts = [
            _dp("Q1", 38.0, date(2021, 4, 1)),
            _dp("Q2", 41.0, date(2021, 4, 1)),
        ]
        cagr, _ = compute_cagr(pts, [])
        assert cagr is None


class TestAnomalyDetection:
    def test_detects_outlier(self):
        eid = uuid.uuid4()
        pts = [
            _dp("FY18", 30.0, date(2017, 4, 1)),
            _dp("FY19", 31.0, date(2018, 4, 1)),
            _dp("FY20", 32.0, date(2019, 4, 1)),
            _dp("FY21", 31.5, date(2020, 4, 1)),
            _dp("FY22", 200.0, date(2021, 4, 1)),  # outlier
        ]
        # z_threshold=1.5: with 5-point series the outlier inflates std_dev
        # (masking effect), so z≈1.79 — still clearly anomalous at threshold 1.5.
        anomalies = detect_anomalies_for_series(pts, eid, z_threshold=1.5)
        assert len(anomalies) >= 1
        assert any(a.period_label == "FY22" for a in anomalies)

    def test_no_anomalies_uniform_series(self):
        eid = uuid.uuid4()
        pts = [_dp(f"FY{y}", 30.0, date(2016 + i, 4, 1)) for i, y in enumerate(range(2017, 2023))]
        anomalies = detect_anomalies_for_series(pts, eid)
        assert anomalies == []

    def test_requires_three_points(self):
        eid = uuid.uuid4()
        pts = [
            _dp("FY21", 30.0, date(2020, 4, 1)),
            _dp("FY22", 90.0, date(2021, 4, 1)),
        ]
        anomalies = detect_anomalies_for_series(pts, eid)
        assert anomalies == []  # < 3 points — no stats

    def test_z_score_direction(self):
        eid = uuid.uuid4()
        pts = [
            _dp(f"FY{i}", 30.0, date(2015 + i, 4, 1)) for i in range(5)
        ] + [_dp("FY20", 100.0, date(2020, 4, 1))]
        anomalies = detect_anomalies_for_series(pts, eid)
        assert anomalies[0].z_score > 0  # above mean


# ---------------------------------------------------------------------------
# Test 3 — Insufficient-Evidence: 4-Layer Structural Enforcement
# ---------------------------------------------------------------------------

from app.services.analytics.why_change_engine import _check_data_derived, WhyChangeResult


class TestInsufficientEvidenceEnforcement:
    """Tests that each IE enforcement layer works independently of the others."""

    # Layer 1: Analytics coverage gate — <2 facts → no LLM call at all
    @pytest.mark.asyncio
    async def test_layer1_no_facts_returns_ie(self):
        """When get_facts returns <2 facts, run_why_change returns insufficient-evidence
        without calling the LLM."""
        mock_db = AsyncMock()
        entity_id = uuid.uuid4()

        with patch(
            "app.services.analytics.why_change_engine.get_facts_for_entity_metric_period",
            new_callable=AsyncMock,
            return_value=[],  # zero facts
        ), patch(
            "app.services.analytics.why_change_engine._run_citation_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            from app.services.analytics.why_change_engine import run_why_change
            result = await run_why_change(
                db=mock_db, entity_id=entity_id, entity_name="Test Entity",
                metric="coal_production", period_year=2022,
            )

        assert result.classification == "insufficient-evidence"
        mock_llm.assert_not_called()  # Layer 1: LLM must NOT be called

    # Layer 2: Semantic relevance gate — all results below threshold → no LLM
    @pytest.mark.asyncio
    async def test_layer2_low_relevance_skips_llm(self):
        """Qdrant results all below SEMANTIC_RELEVANCE_THRESHOLD → LLM not called."""
        mock_db = AsyncMock()
        entity_id = uuid.uuid4()

        from app.models.phase2 import NormalizedFact
        from datetime import date

        def _mock_fact(period_start):
            f = MagicMock(spec=NormalizedFact)
            f.id = uuid.uuid4()
            f.normalized_value = 38.0 + (period_start.year - 2020)
            f.period_start = period_start
            f.period_end = date(period_start.year + 1, 3, 31)
            f.period_label = f"FY{period_start.year + 1}"
            return f

        mock_facts = [
            _mock_fact(date(2020, 4, 1)),
            _mock_fact(date(2021, 4, 1)),
        ]

        with patch(
            "app.services.analytics.why_change_engine.get_facts_for_entity_metric_period",
            new_callable=AsyncMock,
            return_value=mock_facts,
        ), patch(
            "app.services.analytics.why_change_engine.semantic_search",
            new_callable=AsyncMock,
            return_value=[{"score": 0.3, "text_excerpt": "irrelevant text"}],  # below threshold
        ), patch(
            "app.services.analytics.why_change_engine._run_citation_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            from app.services.analytics.why_change_engine import run_why_change
            result = await run_why_change(
                db=mock_db, entity_id=entity_id, entity_name="Test",
                metric="coal_production", period_year=2022,
            )

        mock_llm.assert_not_called()  # Layer 2: no LLM when relevance < threshold
        assert not result.semantic_evidence_found

    # Layer 3: Citation-checking — LLM returns text but empty citations → IE
    @pytest.mark.asyncio
    async def test_layer3_empty_citations_treated_as_ie(self):
        """LLM produces fluent answer text but cited_passage_indices is empty → IE."""
        mock_db = AsyncMock()
        entity_id = uuid.uuid4()

        from datetime import date
        mock_facts = []
        for yr in [2020, 2021]:
            f = MagicMock()
            f.id = uuid.uuid4()
            f.normalized_value = 38.0 + yr - 2020
            f.period_start = date(yr, 4, 1)
            f.period_end = date(yr + 1, 3, 31)
            f.period_label = f"FY{yr + 1}"
            mock_facts.append(f)

        with patch(
            "app.services.analytics.why_change_engine.get_facts_for_entity_metric_period",
            new_callable=AsyncMock,
            return_value=mock_facts,
        ), patch(
            "app.services.analytics.why_change_engine.semantic_search",
            new_callable=AsyncMock,
            return_value=[{"score": 0.85, "text_excerpt": "Some relevant text about coal.", "document_filename": "x.pdf", "page_number": 1, "document_id": str(uuid.uuid4())}],
        ), patch(
            "app.services.analytics.why_change_engine._run_citation_llm",
            new_callable=AsyncMock,
            return_value={
                "answer_text": "Production fell due to monsoon flooding (very plausible-sounding invented reason).",
                "cited_passage_indices": [],       # ← Layer 3: no citations
                "has_sufficient_evidence": False,  # ← LLM self-reports insufficient
                "insufficient_evidence_reason": "no passage supports this",
            },
        ):
            from app.services.analytics.why_change_engine import run_why_change
            result = await run_why_change(
                db=mock_db, entity_id=entity_id, entity_name="Test",
                metric="coal_production", period_year=2022,
            )

        # Classification must NOT be document-supported despite fluent LLM text
        assert result.classification != "document-supported"
        assert result.cited_passages == []
        assert result.llm_explanation == ""  # suppressed

    # Layer 3b: Both conditions must hold — has_sufficient but no indices → IE
    @pytest.mark.asyncio
    async def test_layer3_has_sufficient_true_but_no_indices_treated_as_ie(self):
        """LLM sets has_sufficient_evidence=True but gives empty cited_passage_indices.
        Both conditions must hold → still treated as not document-supported."""
        mock_db = AsyncMock()
        entity_id = uuid.uuid4()

        from datetime import date
        mock_facts = []
        for yr in [2020, 2021]:
            f = MagicMock()
            f.id = uuid.uuid4()
            f.normalized_value = 38.0
            f.period_start = date(yr, 4, 1)
            f.period_end = date(yr + 1, 3, 31)
            f.period_label = f"FY{yr + 1}"
            mock_facts.append(f)

        with patch(
            "app.services.analytics.why_change_engine.get_facts_for_entity_metric_period",
            new_callable=AsyncMock,
            return_value=mock_facts,
        ), patch(
            "app.services.analytics.why_change_engine.semantic_search",
            new_callable=AsyncMock,
            return_value=[{"score": 0.85, "text_excerpt": "text", "document_filename": "a.pdf", "page_number": 2, "document_id": str(uuid.uuid4())}],
        ), patch(
            "app.services.analytics.why_change_engine._run_citation_llm",
            new_callable=AsyncMock,
            return_value={
                "answer_text": "Great answer that cites nothing specifically.",
                "cited_passage_indices": [],   # empty even though has_sufficient=True
                "has_sufficient_evidence": True,
            },
        ):
            from app.services.analytics.why_change_engine import run_why_change
            result = await run_why_change(
                db=mock_db, entity_id=entity_id, entity_name="Test",
                metric="coal_production", period_year=2022,
            )

        assert result.classification != "document-supported"

    # Data-derived classification
    @pytest.mark.asyncio
    async def test_data_derived_when_trend_exists(self):
        """Two consecutive same-direction changes → data-derived, not insufficient."""
        from app.services.analytics.analytics_service import YoYChange

        changes = [
            YoYChange("FY20", "FY21", -2.0, -5.0),
            YoYChange("FY21", "FY22", -1.5, -4.0),
        ]
        classification = await _check_data_derived(changes, "coal_production")
        assert classification == "data-derived"

    @pytest.mark.asyncio
    async def test_insufficient_when_no_trend(self):
        """Mixed direction changes → insufficient-evidence."""
        from app.services.analytics.analytics_service import YoYChange

        changes = [
            YoYChange("FY20", "FY21", 2.0, 5.0),
            YoYChange("FY21", "FY22", -1.5, -4.0),
        ]
        classification = await _check_data_derived(changes, "coal_production")
        assert classification == "insufficient-evidence"


# ---------------------------------------------------------------------------
# Test 4 — ModelGateway: JSON extraction + validation
# ---------------------------------------------------------------------------

from app.services.model_gateway import (
    ModelGatewayError,
    _extract_json,
    _validate_schema,
    _correction_prompt,
)


class TestModelGatewayHelpers:
    def test_extract_plain_json(self):
        text = '{"intent": "analytics", "tasks": []}'
        result = _extract_json(text)
        assert result["intent"] == "analytics"

    def test_extract_json_with_code_fence(self):
        text = '```json\n{"intent": "both"}\n```'
        result = _extract_json(text)
        assert result["intent"] == "both"

    def test_extract_json_with_preamble(self):
        text = 'Here is the JSON:\n{"intent": "semantic"}'
        result = _extract_json(text)
        assert result["intent"] == "semantic"

    def test_validate_required_fields_passes(self):
        schema = {"required": ["intent", "analytics_tasks"]}
        data = {"intent": "analytics", "analytics_tasks": []}
        _validate_schema(data, schema)  # should not raise

    def test_validate_missing_required_raises(self):
        schema = {"required": ["intent", "analytics_tasks"]}
        data = {"intent": "analytics"}  # missing analytics_tasks
        with pytest.raises(ValueError, match="analytics_tasks"):
            _validate_schema(data, schema)

    def test_validate_enum_passes(self):
        schema = {
            "required": ["intent"],
            "properties": {"intent": {"enum": ["analytics", "semantic", "both"]}},
        }
        _validate_schema({"intent": "both"}, schema)  # valid enum

    def test_validate_enum_fails(self):
        schema = {
            "required": ["intent"],
            "properties": {"intent": {"enum": ["analytics", "semantic", "both"]}},
        }
        with pytest.raises(ValueError, match="intent"):
            _validate_schema({"intent": "INVALID"}, schema)

    def test_validate_type_check_fails(self):
        schema = {
            "required": ["count"],
            "properties": {"count": {"type": "integer"}},
        }
        with pytest.raises(ValueError, match="count"):
            _validate_schema({"count": "not-an-int"}, schema)

    def test_correction_prompt_contains_error(self):
        prompt = _correction_prompt("original prompt", '{"bad": json}', "JSONDecodeError")
        assert "JSONDecodeError" in prompt
        assert "CORRECTION REQUIRED" in prompt
        assert "original prompt" in prompt

    def test_extract_json_invalid_raises(self):
        import json
        with pytest.raises(json.JSONDecodeError):
            _extract_json("this is not json at all !!!")


# ---------------------------------------------------------------------------
# Test 5 — Query copilot: intent fallback on gateway failure
# ---------------------------------------------------------------------------

class TestQueryCopilotFallback:
    @pytest.mark.asyncio
    async def test_intent_detection_failure_falls_back_to_semantic(self):
        """If ModelGateway raises ModelGatewayError, intent detection falls back
        to semantic-only mode without crashing."""
        mock_db = AsyncMock()

        with patch(
            "app.services.query_copilot.model_gateway.generate",
            new_callable=AsyncMock,
            side_effect=ModelGatewayError("Ollama overloaded"),
        ), patch(
            "app.services.query_copilot._get_top_entities",
            new_callable=AsyncMock,
            return_value=[],
        ):
            from app.services.query_copilot import _detect_intent
            plan = await _detect_intent(mock_db, "What is coal production?")

        assert plan["intent"] == "semantic"
        assert plan["analytics_tasks"] == []
        assert "Intent detection failed" in plan["planner_notes"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
