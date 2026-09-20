"""Phase 3 — Integration tests (requires running stack: Postgres + Qdrant + Ollama).

Covers the four demo checkpoint scenarios from the Phase 3 spec:

  1. Comparative question → structured comparison + NL explanation + evidence + confidence
  2. Why-change question → document-supported OR explicit insufficient-evidence (never invented)
  3. Fact ID traceability — every cited fact_id in a response traces back via /facts/{id}/evidence
  4. Conflict surfacing — query touching a conflicted fact surfaces it; does not pick a side

Run with:
    python -m pytest test_phase3.py -v --timeout=300

The tests operate on data already in the system from Phases 1–2. If the DB is empty,
most tests will pass in the "insufficient-evidence" path, which is the correct behaviour.

NOTE: These tests make real HTTP requests to the locally-running API (port 8000).
Start the server first: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import uuid
from typing import Any, Dict, Optional

import httpx
import pytest

BASE = "http://localhost:8000"
TIMEOUT = 300  # seconds — LLM calls on CPU can be slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(path: str) -> Dict[str, Any]:
    r = httpx.get(f"{BASE}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    r = httpx.post(f"{BASE}{path}", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _first_entity_id(entity_type: Optional[str] = None) -> Optional[str]:
    """Return the first canonical entity ID in the DB, optionally filtered by type."""
    params = f"?entity_type={entity_type}" if entity_type else ""
    r = httpx.get(f"{BASE}/entities{params}", timeout=30)
    if r.status_code != 200:
        return None
    data = r.json()
    items = data.get("items", [])
    return str(items[0]["id"]) if items else None


def _first_metric_for_entity(entity_id: str) -> Optional[str]:
    """Return the first metric that has data for this entity."""
    r = httpx.get(f"{BASE}/facts?entity_id={entity_id}&page_size=5", timeout=30)
    if r.status_code != 200:
        return None
    items = r.json().get("items", [])
    for item in items:
        if item.get("metric"):
            return item["metric"]
    return None


def _first_conflicted_fact_ids() -> tuple[Optional[str], Optional[str]]:
    """Return (fact_a_id, fact_b_id) of the first open conflict, if any."""
    r = httpx.get(f"{BASE}/conflicts?status=open&page_size=1", timeout=30)
    if r.status_code != 200:
        return None, None
    items = r.json().get("items", [])
    if not items:
        return None, None
    c = items[0]
    return c.get("fact_a_id"), c.get("fact_b_id")


# ---------------------------------------------------------------------------
# Phase 3 Demo Checkpoint 1:
# Comparative question → structured result + NL explanation + evidence + confidence
# ---------------------------------------------------------------------------

class TestComparativeQuery:
    def test_query_endpoint_returns_explainable_response(self):
        """POST /query returns the standard ExplainableAIResponse envelope."""
        response = _post("/query", {
            "question": "What is the coal production trend for all entities?",
            "top_k_semantic": 5,
        })

        # Envelope structure
        assert "query_id" in response
        assert "answer" in response
        assert "evidence" in response
        assert "confidence" in response
        assert "reasoning_type" in response
        assert "conflicts_surfaced" in response

        # Confidence is in valid range
        assert 0 <= response["confidence"] <= 100

        # reasoning_type is one of the four valid values
        assert response["reasoning_type"] in (
            "document-supported", "data-derived",
            "model-inference", "insufficient-evidence",
        )

        # answer is never empty
        assert isinstance(response["answer"], str)
        assert len(response["answer"]) > 0

    def test_analytics_compare_endpoint(self):
        """POST /analytics/compare returns per-entity data points + YoY changes."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No canonical entities in DB — ingest documents first.")

        metric = _first_metric_for_entity(eid)
        if not metric:
            pytest.skip("No normalized facts with metric in DB.")

        response = _post("/analytics/compare", {
            "entity_ids": [eid],
            "metric": metric,
        })

        assert "entities" in response
        assert "all_fact_ids" in response
        assert len(response["entities"]) >= 1

        entity = response["entities"][0]
        assert "data_points" in entity
        assert "yoy_changes" in entity
        assert "entity_name" in entity

        # Every data point has a fact_id
        for dp in entity["data_points"]:
            assert dp.get("fact_id") is not None

    def test_analytics_trend_endpoint(self):
        """POST /analytics/trend returns chronological series with fact_ids."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")

        metric = _first_metric_for_entity(eid)
        if not metric:
            pytest.skip("No facts with metric in DB.")

        response = _post("/analytics/trend", {
            "entity_id": eid,
            "metric": metric,
        })

        assert "series" in response
        assert "all_fact_ids" in response
        assert response["entity_id"] == eid
        assert response["metric"] == metric

    def test_query_persisted_and_retrievable(self):
        """Every /query response is retrievable via GET /query/{id}."""
        post_resp = _post("/query", {
            "question": "Summarise available coal production data.",
            "top_k_semantic": 3,
        })
        query_id = post_resp["query_id"]

        get_resp = _get(f"/query/{query_id}")

        assert get_resp["query_id"] == query_id
        assert get_resp["question"] == "Summarise available coal production data."
        assert "model_used_intent" in get_resp    # audit field
        assert "model_used_synthesis" in get_resp
        assert "intent_plan" in get_resp


# ---------------------------------------------------------------------------
# Phase 3 Demo Checkpoint 2:
# Why-change → document-supported OR explicit "no evidence" (never invented cause)
# ---------------------------------------------------------------------------

class TestWhyChangeQuery:
    def test_why_change_endpoint_returns_valid_response(self):
        """POST /analytics/why-did-this-change always returns a valid response."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")
        metric = _first_metric_for_entity(eid)
        if not metric:
            pytest.skip("No facts in DB.")

        response = _post("/analytics/why-did-this-change", {
            "entity_id": eid,
            "metric": metric,
            "period_year": 2022,
            "top_k_semantic": 5,
        })

        assert "answer" in response
        assert "reasoning_type" in response
        assert "why_change_detail" in response
        assert 0 <= response["confidence"] <= 100

    def test_why_change_never_invents_cause(self):
        """When evidence is insufficient, response must say so explicitly —
        not contain a plausible-sounding invented explanation."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")

        # Use a metric/year unlikely to have document-level explanations
        response = _post("/analytics/why-did-this-change", {
            "entity_id": eid,
            "metric": "seam_depth",
            "period_year": 2019,
            "top_k_semantic": 3,
        })

        rt = response["reasoning_type"]
        if rt == "insufficient-evidence":
            # Must contain the canned message — no invented content
            assert "No sufficient evidence" in response["answer"] or \
                   "No documented explanation" in response["answer"] or \
                   "no sufficient" in response["answer"].lower()
            # cited_passages must be empty
            detail = response.get("why_change_detail", {})
            assert detail.get("cited_passages", []) == []

        elif rt == "document-supported":
            # Must have at least one cited passage
            detail = response.get("why_change_detail", {})
            assert len(detail.get("cited_passages", [])) > 0

        elif rt == "data-derived":
            # May have empty citations (correlation from data, not documents)
            assert "trend" in response["answer"].lower() or \
                   "pattern" in response["answer"].lower() or \
                   "changed" in response["answer"].lower()

    def test_why_change_via_query_endpoint(self):
        """Why-change can also be triggered indirectly via /query."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")

        # Look up entity name first
        r = httpx.get(f"{BASE}/entities/{eid}", timeout=30)
        entity_name = r.json().get("canonical_name", "the entity") if r.status_code == 200 else "the entity"

        response = _post("/query", {
            "question": f"Why did coal production change for {entity_name} in 2022?",
            "top_k_semantic": 5,
        })

        assert "answer" in response
        assert response["reasoning_type"] in (
            "document-supported", "data-derived",
            "model-inference", "insufficient-evidence",
        )


# ---------------------------------------------------------------------------
# Phase 3 Demo Checkpoint 3:
# Fact ID traceability — every cited fact_id traces back via /facts/{id}/evidence
# ---------------------------------------------------------------------------

class TestFactIdTraceability:
    def test_every_evidence_fact_id_is_resolvable(self):
        """Every fact_id in a response's evidence list resolves via /facts/{id}/evidence."""
        response = _post("/query", {
            "question": "What coal production data is available?",
            "top_k_semantic": 5,
        })

        evidence_items = response.get("evidence", [])
        if not evidence_items:
            pytest.skip("No evidence items in response — may be insufficient-evidence path.")

        for item in evidence_items[:3]:  # spot-check first 3
            fact_id = item["fact_id"]
            evidence_resp = _get(f"/facts/{fact_id}/evidence")

            # Full lineage chain must be present
            assert "fact" in evidence_resp
            assert "extracted" in evidence_resp
            assert "document" in evidence_resp
            assert "page" in evidence_resp

            # The fact_id must match
            assert evidence_resp["fact"]["id"] == fact_id

    def test_analytics_compare_fact_ids_all_resolvable(self):
        """Every fact_id in an analytics/compare response resolves via /facts/{id}/evidence."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")
        metric = _first_metric_for_entity(eid)
        if not metric:
            pytest.skip("No facts in DB.")

        response = _post("/analytics/compare", {
            "entity_ids": [eid],
            "metric": metric,
        })

        all_fact_ids = response.get("all_fact_ids", [])
        if not all_fact_ids:
            pytest.skip("No fact_ids in compare response.")

        # Spot-check up to 3 fact IDs
        for fid in all_fact_ids[:3]:
            ev = _get(f"/facts/{fid}/evidence")
            assert ev["fact"]["id"] == fid
            assert ev["fact"]["metric"] == metric  # verify metric matches

    def test_why_change_cited_fact_ids_resolvable(self):
        """Fact IDs from why-change response resolve with correct entity."""
        eid = _first_entity_id()
        if not eid:
            pytest.skip("No entities in DB.")
        metric = _first_metric_for_entity(eid)
        if not metric:
            pytest.skip("No facts in DB.")

        response = _post("/analytics/why-did-this-change", {
            "entity_id": eid,
            "metric": metric,
            "period_year": 2022,
        })

        detail = response.get("why_change_detail", {})
        for fid_key in ("fact_id_from", "fact_id_to"):
            fid = detail.get(fid_key)
            if fid:
                ev = _get(f"/facts/{fid}/evidence")
                assert ev["fact"]["id"] == fid
                # Entity must match
                if ev.get("entity"):
                    assert ev["entity"]["id"] == eid


# ---------------------------------------------------------------------------
# Phase 3 Demo Checkpoint 4:
# Conflict surfacing — query touching conflicted fact surfaces it; no silent resolution
# ---------------------------------------------------------------------------

class TestConflictSurfacing:
    def test_conflicted_fact_surfaces_conflict_in_query(self):
        """When a query retrieves a fact with an open conflict, the conflict appears
        in conflicts_surfaced and the answer does NOT silently pick one side."""
        fact_a_id, fact_b_id = _first_conflicted_fact_ids()
        if not fact_a_id:
            pytest.skip("No open conflicts in DB — run Phase 2 pipeline on conflicting documents.")

        # Get the entity/metric/period of the conflicted fact
        ev = _get(f"/facts/{fact_a_id}/evidence")
        entity_id = ev.get("entity", {}).get("id")
        metric = ev["fact"].get("metric")
        if not entity_id or not metric:
            pytest.skip("Conflicted fact missing entity or metric.")

        entity_name = ev.get("entity", {}).get("canonical_name", "entity")

        response = _post("/query", {
            "question": f"What is the {metric.replace('_', ' ')} for {entity_name}?",
            "top_k_semantic": 5,
        })

        # Conflict must be surfaced — not silently resolved
        surfaced = response.get("conflicts_surfaced", [])
        assert len(surfaced) >= 1, (
            "Expected at least one conflict to be surfaced in the response, "
            "but conflicts_surfaced is empty. The system must not silently ignore conflicts."
        )

        # Verify conflict details are present and coherent
        conflict = surfaced[0]
        assert "conflict_id" in conflict
        assert "fact_a_id" in conflict
        assert "fact_b_id" in conflict
        assert "description" in conflict
        assert conflict["status"] == "open"

    def test_conflicted_entity_analytics_marks_has_conflict(self):
        """Analytics compare endpoint marks has_conflict=True on conflicted data points."""
        fact_a_id, _ = _first_conflicted_fact_ids()
        if not fact_a_id:
            pytest.skip("No open conflicts in DB.")

        ev = _get(f"/facts/{fact_a_id}/evidence")
        entity_id = ev.get("entity", {}).get("id")
        metric = ev["fact"].get("metric")
        if not entity_id or not metric:
            pytest.skip("Conflicted fact missing entity or metric.")

        response = _post("/analytics/compare", {
            "entity_ids": [entity_id],
            "metric": metric,
        })

        entities = response.get("entities", [])
        assert entities, "No entity data returned."

        all_data_points = [dp for e in entities for dp in e.get("data_points", [])]
        conflicted_points = [dp for dp in all_data_points if dp.get("has_conflict")]

        assert len(conflicted_points) >= 1, (
            "Expected at least one data point with has_conflict=True for a fact "
            "that is involved in an open conflict record."
        )

    def test_conflict_not_silently_resolved_in_answer(self):
        """The answer text must not assert a single definitive value when there is a conflict
        without acknowledging the data conflict."""
        fact_a_id, fact_b_id = _first_conflicted_fact_ids()
        if not fact_a_id:
            pytest.skip("No open conflicts in DB.")

        ev = _get(f"/facts/{fact_a_id}/evidence")
        entity_name = ev.get("entity", {}).get("canonical_name", "entity")
        metric = ev["fact"].get("metric", "coal production")

        response = _post("/query", {
            "question": f"What is {metric.replace('_', ' ')} for {entity_name}?",
            "top_k_semantic": 5,
        })

        surfaced = response.get("conflicts_surfaced", [])

        # If conflicts_surfaced is non-empty, the answer must not be "pristine confident"
        if surfaced:
            # Confidence must be penalised by the conflict (cv_score = 0.3 for conflicted facts)
            assert response["confidence"] < 95, (
                "When open conflicts are present, confidence should be penalised. "
                f"Got {response['confidence']}/100 with {len(surfaced)} open conflicts."
            )


# ---------------------------------------------------------------------------
# Smoke tests — basic endpoint availability
# ---------------------------------------------------------------------------

class TestEndpointAvailability:
    def test_health(self):
        r = _get("/health")
        assert r["status"] == "ok"
        assert "phase3" in r["version"]

    def test_query_404_on_missing_id(self):
        r = httpx.get(f"{BASE}/query/{uuid.uuid4()}", timeout=30)
        assert r.status_code == 404

    def test_analytics_compare_404_on_no_data(self):
        r = httpx.post(f"{BASE}/analytics/compare", json={
            "entity_ids": [str(uuid.uuid4())],  # random non-existent entity
            "metric": "coal_production",
        }, timeout=30)
        assert r.status_code == 404

    def test_analytics_trend_404_on_no_data(self):
        r = httpx.post(f"{BASE}/analytics/trend", json={
            "entity_id": str(uuid.uuid4()),
            "metric": "coal_production",
        }, timeout=30)
        assert r.status_code == 404

    def test_why_change_404_on_missing_entity(self):
        r = httpx.post(f"{BASE}/analytics/why-did-this-change", json={
            "entity_id": str(uuid.uuid4()),
            "metric": "coal_production",
            "period_year": 2022,
        }, timeout=30)
        assert r.status_code == 404

    def test_query_rejects_empty_question(self):
        r = httpx.post(f"{BASE}/query", json={"question": "  "}, timeout=30)
        assert r.status_code == 422  # Pydantic validation: min_length=3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=300"])
