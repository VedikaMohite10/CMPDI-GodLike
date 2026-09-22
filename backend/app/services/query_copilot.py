"""AI Query & Response Copilot — full retrieval pipeline.

Fixed pipeline (no agentic loops, no autonomous tool-calling):

  User Question
       ↓
  Intent Detection  — LLM (7b), constrained JSON, entity list pre-filtered by embedding
       ↓
  Query Planner     — parses intent plan into internal service calls
       ↓
  Retrieve          — Qdrant semantic search AND/OR Analytics Service structured retrieval
       ↓
  Calculate         — Analytics Service ONLY (never LLM)
       ↓
  Validate          — check retrieved facts for open conflicts (Phase 2 conflicts table)
       ↓
  Generate Answer   — LLM (14b) synthesis strictly from retrieved evidence + calculated results
       ↓
  Package           — Explainer module → ExplainableAIResponse
       ↓
  Persist           — save to query_responses table

Design guarantees:
  - LLM never performs arithmetic
  - LLM never introduces facts not in the passed context
  - 4-layer insufficient-evidence enforcement (see explainer + why_change_engine)
  - Every open conflict touching a retrieved fact is surfaced, never silently suppressed
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.phase2 import CanonicalEntity, QueryResponse
from app.schemas.query import ExplainableAIResponse
from app.services import model_gateway
from app.services.analytics import analytics_service
from app.services.analytics.analytics_service import (
    ComparisonResult,
    TrendResult,
    get_open_conflicts_for_facts,
)
from app.services.explainer import package_response
from app.services.vector.qdrant_indexer import semantic_search

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Intent detection JSON schema (validated by ModelGateway)
# ---------------------------------------------------------------------------

_INTENT_SCHEMA: Dict[str, Any] = {
    "required": ["intent", "analytics_tasks", "planner_notes"],
    "properties": {
        "intent": {"type": "string", "enum": ["analytics", "semantic", "both"]},
        "analytics_tasks": {"type": "array"},
        "semantic_query": {},
        "why_change_request": {},
        "planner_notes": {"type": "string"},
    },
}

_INTENT_SYSTEM = (
    "You are a query planner for a coal mining analytics system. "
    "Your ONLY job is to classify a user question and produce a JSON retrieval plan. "
    "You NEVER answer the question yourself. You NEVER compute numbers. "
    "You output ONLY valid JSON conforming to the schema provided."
)

_SYNTHESIS_SYSTEM = (
    "You are a factual synthesizer for a coal mining analytics system. "
    "You will receive pre-calculated numeric results and retrieved document passages.\n\n"
    "STRICT RULES:\n"
    "1. Use ONLY the numbers from the provided calculation results. Do NOT compute or modify any number.\n"
    "2. Use ONLY content from the retrieved passages for explanations. Do NOT add external knowledge.\n"
    "3. For EVERY explanatory claim, cite the passage index using [P0], [P1], etc.\n"
    "4. If no passage supports a claim, do NOT make that claim.\n"
    "5. Respond ONLY with valid JSON. No code fences. No explanation outside the JSON.\n"
    "6. If you have insufficient evidence, set has_sufficient_evidence to false."
)

_SYNTHESIS_SCHEMA: Dict[str, Any] = {
    "required": ["answer_text", "cited_passage_indices", "has_sufficient_evidence"],
    "properties": {
        "answer_text": {"type": "string"},
        "cited_passage_indices": {"type": "array"},
        "has_sufficient_evidence": {"type": "boolean"},
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_query(
    db: AsyncSession,
    question: str,
    top_k_semantic: int = 10,
) -> ExplainableAIResponse:
    """Execute the full query pipeline and return a packaged ExplainableAIResponse."""
    query_id = uuid.uuid4()

    # ── Step 1: Intent detection ─────────────────────────────────────────
    intent_plan = await _detect_intent(db, question)
    intent = intent_plan.get("intent", "semantic")
    analytics_tasks = intent_plan.get("analytics_tasks", [])
    semantic_query_str = intent_plan.get("semantic_query") or question
    why_change_req = intent_plan.get("why_change_request")

    logger.info(
        "Query %s: intent=%s, tasks=%d, why_change=%s",
        query_id, intent, len(analytics_tasks), bool(why_change_req),
    )

    # ── Step 2 & 3: Retrieve + Calculate ─────────────────────────────────
    all_fact_ids: List[uuid.UUID] = []
    analytics_result: Optional[Any] = None
    calculation_parts: List[str] = []
    tasks_planned = len(analytics_tasks)
    tasks_with_results = 0

    if intent in ("analytics", "both") and analytics_tasks:
        analytics_result, calc_strs, task_fact_ids, tasks_with_results = await _run_analytics_tasks(
            db, analytics_tasks
        )
        all_fact_ids.extend(task_fact_ids)
        calculation_parts.extend(calc_strs)

    # Semantic retrieval (always for "both", and "semantic"; also supplements analytics)
    semantic_passages: List[Dict[str, Any]] = []
    if intent in ("semantic", "both") and semantic_query_str:
        raw_semantic = await _semantic_retrieve(semantic_query_str, top_k_semantic)
        semantic_passages = raw_semantic

    # ── Step 4: Conflict validation ───────────────────────────────────────
    conflicts = await get_open_conflicts_for_facts(db, all_fact_ids)

    # ── Layer 1 gate: short-circuit if no analytics results and semantic-only failed ──
    if intent == "analytics" and tasks_planned > 0 and tasks_with_results == 0:
        logger.info("Query %s: Layer-1 IE gate triggered (no analytics results)", query_id)
        response = await package_response(
            db=db,
            query_id=query_id,
            question=question,
            answer=_insufficient_evidence_answer(question),
            fact_ids=[],
            conflicts=[],
            reasoning_type="insufficient-evidence",
            tasks_planned=tasks_planned,
            tasks_with_results=0,
        )
        await _persist_response(db, query_id, question, response, intent_plan)
        return response

    # ── Step 5: Generate answer ───────────────────────────────────────────
    # Filter semantic passages by relevance threshold (Layer 2 gate)
    relevant_passages = [
        p for p in semantic_passages
        if p.get("score", 0) >= settings.SEMANTIC_RELEVANCE_THRESHOLD
    ]

    synthesis_result = await _synthesize_answer(
        question=question,
        analytics_result=analytics_result,
        calculation_parts=calculation_parts,
        passages=relevant_passages,
        conflicts=conflicts,
    )

    # Layer 3 gate: citation check
    cited_indices = synthesis_result.get("cited_passage_indices", [])
    has_sufficient = synthesis_result.get("has_sufficient_evidence", False)
    answer_text = synthesis_result.get("answer_text", "")

    # Determine reasoning type
    if analytics_result is not None and tasks_with_results > 0:
        if has_sufficient and cited_indices:
            reasoning_type: str = "document-supported"
        elif tasks_with_results > 0:
            reasoning_type = "data-derived"
        else:
            reasoning_type = "insufficient-evidence"
    elif has_sufficient and cited_indices:
        reasoning_type = "document-supported"
    elif not cited_indices and not tasks_with_results:
        reasoning_type = "insufficient-evidence"
    else:
        reasoning_type = "model-inference"

    # Suppress non-cited LLM text for insufficient-evidence
    if reasoning_type == "insufficient-evidence":
        answer_text = _insufficient_evidence_answer(question)

    # Add semantic-result fact references to evidence (non-analytics path)
    semantic_evidence_fact_ids = _extract_fact_ids_from_passages(relevant_passages, cited_indices)
    all_fact_ids.extend(semantic_evidence_fact_ids)

    # ── Step 6: Package via Explainer ─────────────────────────────────────
    calculation_str = "; ".join(calculation_parts) if calculation_parts else None

    response = await package_response(
        db=db,
        query_id=query_id,
        question=question,
        answer=answer_text,
        fact_ids=all_fact_ids,
        conflicts=conflicts,
        reasoning_type=reasoning_type,  # type: ignore[arg-type]
        calculation=calculation_str,
        analytics_results=_serialise_analytics(analytics_result),
        tasks_planned=tasks_planned,
        tasks_with_results=tasks_with_results,
    )

    # ── Step 7: Persist ───────────────────────────────────────────────────
    await _persist_response(db, query_id, question, response, intent_plan)
    return response


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

async def _detect_intent(db: AsyncSession, question: str) -> Dict[str, Any]:
    """Run the intent-detection LLM call (7b model, constrained JSON output).

    Pre-filters canonical entities by embedding similarity (PLANNER_ENTITY_TOP_K)
    to keep context size manageable as the entity table grows.
    """
    # Load entities — pre-filter by embedding similarity
    entity_list = await _get_top_entities(db, question)
    from app.services.phase2.metric_registry import CANONICAL_METRICS
    metric_list = list(CANONICAL_METRICS.keys())

    entity_json = [
        {"id": str(e.id), "name": e.canonical_name, "type": e.entity_type}
        for e in entity_list
    ]

    user_prompt = (
        f'User question: "{question}"\n\n'
        f"Available canonical entities (select entity_ids only from this list):\n"
        f"{entity_json}\n\n"
        f"Available canonical metrics (use metric key only from this list):\n"
        f"{metric_list}\n\n"
        "Return ONLY this JSON:\n"
        "{\n"
        '  "intent": "analytics|semantic|both",\n'
        '  "analytics_tasks": [\n'
        '    {\n'
        '      "type": "yoy_change|cagr|trend|compare|anomaly_detect",\n'
        '      "entity_ids": ["<uuid from entity list above>"],\n'
        '      "metric": "<canonical_metric_key from metric list above>",\n'
        '      "period_start_year": null,\n'
        '      "period_end_year": null\n'
        '    }\n'
        '  ],\n'
        '  "semantic_query": "<refined search string or null>",\n'
        '  "why_change_request": null,\n'
        '  "planner_notes": "<max 50 words>"\n'
        "}"
    )

    try:
        plan = await model_gateway.generate(
            prompt=user_prompt,
            role="intent",
            system=_INTENT_SYSTEM,
            json_schema=_INTENT_SCHEMA,
        )
        return plan  # type: ignore[return-value]
    except model_gateway.ModelGatewayError as exc:
        logger.warning("Intent detection failed: %s. Falling back to semantic-only.", exc)
        return {
            "intent": "semantic",
            "analytics_tasks": [],
            "semantic_query": question,
            "why_change_request": None,
            "planner_notes": f"Intent detection failed: {exc}",
        }


async def _get_top_entities(db: AsyncSession, question: str) -> List[CanonicalEntity]:
    """Return top PLANNER_ENTITY_TOP_K entities most similar to the question.

    Embeds the question, then scores entity names by cosine similarity.
    Falls back to returning all entities if embedding fails.
    """
    result = await db.execute(select(CanonicalEntity))
    all_entities = list(result.scalars().all())

    if len(all_entities) <= settings.PLANNER_ENTITY_TOP_K:
        return all_entities

    try:
        q_vec = await model_gateway.embed(question)
        entity_texts = [e.canonical_name for e in all_entities]
        entity_vecs = await model_gateway.embed_batch(entity_texts)

        scored = []
        for entity, evec in zip(all_entities, entity_vecs):
            score = _cosine(q_vec, evec)
            scored.append((score, entity))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:settings.PLANNER_ENTITY_TOP_K]]

    except Exception as exc:
        logger.warning("Entity pre-filtering failed: %s. Using all entities.", exc)
        return all_entities


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------------------
# Analytics task execution
# ---------------------------------------------------------------------------

async def _run_analytics_tasks(
    db: AsyncSession,
    tasks: List[Dict[str, Any]],
) -> tuple[Optional[Any], List[str], List[uuid.UUID], int]:
    """Execute all analytics tasks from the intent plan.

    Returns (combined_result, calculation_strings, all_fact_ids, tasks_with_results).
    Uses ComparisonResult as the unified return type (works for single and multi-entity).
    """
    all_fact_ids: List[uuid.UUID] = []
    calc_strs: List[str] = []
    results: List[Any] = []
    tasks_with_results = 0

    for task in tasks:
        task_type = task.get("type", "compare")
        metric = task.get("metric")
        entity_ids_raw = task.get("entity_ids", [])
        start_year = task.get("period_start_year")
        end_year = task.get("period_end_year")

        if not metric or not entity_ids_raw:
            logger.debug("Skipping malformed analytics task: %s", task)
            continue

        try:
            entity_ids = [uuid.UUID(eid) for eid in entity_ids_raw]
        except (ValueError, AttributeError):
            logger.warning("Could not parse entity_ids: %s", entity_ids_raw)
            continue

        try:
            if task_type == "trend" and len(entity_ids) == 1:
                result = await analytics_service.get_trend(
                    db, entity_ids[0], metric, start_year, end_year
                )
                fact_ids = result.all_fact_ids
                calc_str = _trend_calc_string(result)
            else:
                # Default to comparison (covers compare, yoy_change, cagr, anomaly_detect)
                result = await analytics_service.get_comparison(
                    db, entity_ids, metric, start_year, end_year
                )
                fact_ids = result.all_fact_ids
                calc_str = _comparison_calc_string(result)

            if fact_ids:
                tasks_with_results += 1
                all_fact_ids.extend(fact_ids)
                results.append(result)
                calc_strs.append(calc_str)

        except Exception as exc:
            logger.warning("Analytics task %s failed: %s", task_type, exc)

    combined = results[0] if len(results) == 1 else (results if results else None)
    return combined, calc_strs, all_fact_ids, tasks_with_results


def _trend_calc_string(result: TrendResult) -> str:
    pts = [(dp.period_label, dp.value) for dp in result.series if dp.value is not None]
    if not pts:
        return f"Trend ({result.metric}): no data"
    parts = [f"{lbl}: {val} {result.unit or ''}" for lbl, val in pts]
    return f"Trend for {result.entity_name} / {result.metric}: " + ", ".join(parts)


def _comparison_calc_string(result: ComparisonResult) -> str:
    parts = []
    for e in result.entities:
        if e.yoy_changes:
            for yoy in e.yoy_changes:
                parts.append(
                    f"{e.entity_name} {yoy.from_period}→{yoy.to_period}: "
                    f"YoY = ({yoy.to_period}_value - {yoy.from_period}_value) / "
                    f"{yoy.from_period}_value × 100 = {yoy.pct_change or 0:.1f}%"
                )
        if e.cagr_pct is not None:
            parts.append(f"{e.entity_name} CAGR = {e.cagr_pct:.2f}%")
    return "; ".join(parts) if parts else f"Comparison for {result.metric}: computed"


# ---------------------------------------------------------------------------
# Semantic retrieval
# ---------------------------------------------------------------------------

async def _semantic_retrieve(query: str, top_k: int) -> List[Dict[str, Any]]:
    try:
        return await semantic_search(query=query, top_k=top_k)
    except Exception as exc:
        logger.warning("Semantic search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Answer synthesis (14b model, strictly grounded)
# ---------------------------------------------------------------------------

async def _synthesize_answer(
    question: str,
    analytics_result: Optional[Any],
    calculation_parts: List[str],
    passages: List[Dict[str, Any]],
    conflicts: list,
) -> Dict[str, Any]:
    """Build the synthesis prompt and call the 14b model."""
    calc_block = "\n".join(calculation_parts) if calculation_parts else "(no calculations performed)"
    passages_text = "\n\n".join(
        f"[P{i}] (Doc: {p.get('document_filename', 'unknown')}, "
        f"Page: {p.get('page_number', '?')})\n{p.get('text_excerpt', '')[:800]}"
        for i, p in enumerate(passages)
    ) if passages else "(no document passages retrieved)"

    conflict_block = ""
    if conflicts:
        conflict_block = "\n\nDATA CONFLICTS (must be mentioned in the answer):\n"
        for c in conflicts:
            conflict_block += (
                f"- Conflict: {c.value_a} {c.unit_a or ''} vs {c.value_b} {c.unit_b or ''} "
                f"(delta {c.delta_pct:.1f}% — status: {c.status})\n"
            )

    user_prompt = (
        f'User question: "{question}"\n\n'
        f"PRE-CALCULATED RESULTS (use these numbers exactly, do not recompute):\n"
        f"{calc_block}\n"
        f"{conflict_block}\n"
        f"RETRIEVED DOCUMENT PASSAGES:\n{passages_text}\n\n"
        "Synthesize a factual answer. Return ONLY this JSON:\n"
        "{\n"
        '  "answer_text": "...",\n'
        '  "cited_passage_indices": [0, 1],\n'
        '  "has_sufficient_evidence": true,\n'
        '  "insufficient_evidence_reason": null\n'
        "}"
    )

    # If there are no passages AND no analytics results, skip LLM entirely
    if not passages and not calculation_parts:
        return {
            "answer_text": "",
            "cited_passage_indices": [],
            "has_sufficient_evidence": False,
            "insufficient_evidence_reason": "No analytics data or document passages available.",
        }

    try:
        result = await model_gateway.generate(
            prompt=user_prompt,
            role="synthesis",
            system=_SYNTHESIS_SYSTEM,
            json_schema=_SYNTHESIS_SCHEMA,
        )
        return result  # type: ignore[return-value]
    except model_gateway.ModelGatewayError as exc:
        logger.warning("Synthesis LLM failed: %s", exc)
        return {
            "answer_text": "",
            "cited_passage_indices": [],
            "has_sufficient_evidence": False,
            "insufficient_evidence_reason": str(exc),
        }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

async def _persist_response(
    db: AsyncSession,
    query_id: uuid.UUID,
    question: str,
    response: ExplainableAIResponse,
    intent_plan: Dict[str, Any],
) -> None:
    """Persist the query response to the query_responses table."""
    record = QueryResponse(
        id=query_id,
        question=question,
        answer=response.answer,
        evidence=[item.model_dump(mode="json") for item in response.evidence],
        conflicts_surfaced=[c.model_dump(mode="json") for c in response.conflicts_surfaced],
        analytics_results=response.analytics_results,
        calculation=response.calculation,
        confidence=response.confidence,
        reasoning_type=response.reasoning_type,
        intent_plan=intent_plan,
        model_used_intent=settings.INTENT_LLM_MODEL,
        model_used_synthesis=settings.SYNTHESIS_LLM_MODEL,
    )
    db.add(record)
    try:
        await db.commit()
        logger.info("Query %s persisted to query_responses.", query_id)
    except Exception as exc:
        logger.warning("Could not persist query response %s: %s", query_id, exc)
        await db.rollback()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _insufficient_evidence_answer(question: str) -> str:
    return (
        "No sufficient evidence found in the available documents to answer this question. "
        "The system did not find any matching normalized data or relevant document passages "
        "for the entities, metrics, or time periods referenced in your query. "
        "Please verify that the relevant documents have been ingested and processed through "
        "the Phase 2 pipeline."
    )


def _serialise_analytics(result: Optional[Any]) -> Optional[Dict[str, Any]]:
    """Convert an analytics result dataclass to a JSON-serialisable dict."""
    if result is None:
        return None
    try:
        import dataclasses
        if dataclasses.is_dataclass(result):
            return _dc_to_dict(result)
        if isinstance(result, list):
            return {"results": [_dc_to_dict(r) if dataclasses.is_dataclass(r) else r for r in result]}
    except Exception:
        pass
    return None


def _dc_to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to dicts, UUID to str, date to isoformat."""
    import dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dc_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_dc_to_dict(i) for i in obj]
    return obj


def _extract_fact_ids_from_passages(
    passages: List[Dict[str, Any]],
    cited_indices: List[int],
) -> List[uuid.UUID]:
    """For semantic-only results, we don't have direct fact_ids from passages.
    This placeholder returns empty — evidence is built from passages in the explainer
    via the block_id→fact lineage when the full Qdrant→Postgres bridge is queried.
    Phase 4 can enhance this with a block_id→fact lookup.
    """
    return []
