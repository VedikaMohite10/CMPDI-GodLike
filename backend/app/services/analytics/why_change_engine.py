"""Why-Did-This-Change Engine — 5-step pipeline.

Step 1: Compute the numeric change using the Analytics Service (deterministic).
Step 2: Semantic retrieval from Qdrant — scoped to entity/metric/period.
Step 3: LLM citation analysis — constrained JSON output, synthesis model (14b).
Step 4: Classification → document-supported | data-derived | insufficient-evidence.
Step 5: Return WhyChangeResult with evidence, cited passages, classification.

Critical: the LLM CANNOT bypass the insufficient-evidence gate by writing fluent text
without citations. Layer-3 post-generation check enforces this structurally.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.phase2 import NormalizedFact
from app.services import model_gateway
from app.services.analytics.analytics_service import (
    DataPoint,
    YoYChange,
    compute_yoy,
    get_facts_for_entity_metric_period,
    get_open_conflicts_for_facts,
)
from app.services.vector.qdrant_indexer import semantic_search

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class CitedPassageResult:
    document_id:       uuid.UUID
    document_filename: str
    page_number:       Optional[int]
    excerpt:           str


@dataclass
class WhyChangeResult:
    # The numeric change (from Analytics Service)
    from_value:      Optional[float]
    to_value:        Optional[float]
    pct_change:      Optional[float]
    fact_id_from:    Optional[uuid.UUID]
    fact_id_to:      Optional[uuid.UUID]

    # Classification
    classification:  str  # "document-supported" | "data-derived" | "insufficient-evidence"

    # Evidence for the Explainable AI module
    cited_passages:  List[CitedPassageResult] = field(default_factory=list)
    all_fact_ids:    List[uuid.UUID]          = field(default_factory=list)

    # Raw semantic results (before citation check) — kept for confidence scoring
    semantic_results_count: int  = 0
    semantic_evidence_found: bool = False

    # Human-readable explanation text (may be empty for insufficient-evidence)
    llm_explanation: str = ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_why_change(
    db: AsyncSession,
    entity_id: uuid.UUID,
    entity_name: str,
    metric: str,
    period_year: int,
    top_k: int = 10,
) -> WhyChangeResult:
    """Execute the full 5-step Why-Change pipeline.

    Returns a WhyChangeResult. Never raises on insufficient evidence — instead
    returns classification="insufficient-evidence" with empty cited_passages.
    """

    # ── Step 1: Compute the numeric change ──────────────────────────────
    facts = await get_facts_for_entity_metric_period(db, entity_id, metric, period_year)

    if len(facts) < 2:
        # Layer 1 gate: cannot compute a change with <2 data points
        logger.info(
            "Why-change: insufficient facts for %s/%s/%d (found %d)",
            entity_name, metric, period_year, len(facts),
        )
        return WhyChangeResult(
            from_value=None, to_value=None, pct_change=None,
            fact_id_from=None, fact_id_to=None,
            classification="insufficient-evidence",
            llm_explanation="",
            all_fact_ids=[f.id for f in facts],
        )

    all_fact_ids = [f.id for f in facts]

    # Sort facts by period and find the transition around the queried year
    fact_data_points = _facts_to_data_points(facts)
    yoy_changes = compute_yoy(fact_data_points)

    # Find the change closest to the queried year
    target_change = _find_target_change(yoy_changes, fact_data_points, period_year)
    if target_change is None:
        return WhyChangeResult(
            from_value=None, to_value=None, pct_change=None,
            fact_id_from=None, fact_id_to=None,
            classification="insufficient-evidence",
            llm_explanation="",
            all_fact_ids=all_fact_ids,
        )

    from_val, to_val = _get_values_from_change(target_change, fact_data_points)
    fact_from_id = target_change.fact_ids_used[0] if len(target_change.fact_ids_used) > 0 else None
    fact_to_id   = target_change.fact_ids_used[1] if len(target_change.fact_ids_used) > 1 else None

    # ── Step 2: Semantic retrieval — scoped to entity/metric/period ──────
    semantic_query = (
        f"{entity_name} {metric.replace('_', ' ')} {period_year} "
        f"change reason explanation"
    )

    try:
        raw_results = await semantic_search(query=semantic_query, top_k=top_k)
    except Exception as exc:
        logger.warning("Why-change: Qdrant search failed: %s", exc)
        raw_results = []

    # Layer 2 gate: discard results below relevance threshold
    threshold = settings.SEMANTIC_RELEVANCE_THRESHOLD
    relevant_results = [r for r in raw_results if r.get("score", 0) >= threshold]

    semantic_evidence_found = len(relevant_results) > 0
    logger.debug(
        "Why-change: %d semantic results, %d above threshold %.2f",
        len(raw_results), len(relevant_results), threshold,
    )

    # ── Step 3: LLM citation analysis ────────────────────────────────────
    if not semantic_evidence_found:
        # Skip LLM entirely — no evidence to reason over
        return WhyChangeResult(
            from_value=from_val,
            to_value=to_val,
            pct_change=target_change.pct_change,
            fact_id_from=fact_from_id,
            fact_id_to=fact_to_id,
            classification=await _check_data_derived(yoy_changes, metric),
            llm_explanation="",
            cited_passages=[],
            all_fact_ids=all_fact_ids,
            semantic_results_count=len(raw_results),
            semantic_evidence_found=False,
        )

    # Build passage list for the prompt
    passages = _build_passages(relevant_results)
    llm_result = await _run_citation_llm(
        entity_name=entity_name,
        metric=metric,
        period_year=period_year,
        from_value=from_val,
        to_value=to_val,
        pct_change=target_change.pct_change,
        passages=passages,
    )

    # ── Step 4: Classification based on Layer-3 citation check ───────────
    cited_indices = llm_result.get("cited_passage_indices", [])
    has_sufficient = llm_result.get("has_sufficient_evidence", False)
    answer_text = llm_result.get("answer_text", "")

    # Layer 3 gate: both conditions must hold for document-supported
    if has_sufficient and cited_indices:
        classification = "document-supported"
        cited_passages = [
            CitedPassageResult(
                document_id=uuid.UUID(passages[i]["document_id"]),
                document_filename=passages[i].get("document_filename", ""),
                page_number=passages[i].get("page_number"),
                excerpt=passages[i].get("excerpt", ""),
            )
            for i in cited_indices
            if isinstance(i, int) and 0 <= i < len(passages)
        ]
    else:
        # LLM found no cited evidence — fall back to data-derived or insufficient
        classification = await _check_data_derived(yoy_changes, metric)
        cited_passages = []
        answer_text = ""  # suppress non-cited LLM text

    # ── Step 5: Return result ─────────────────────────────────────────────
    return WhyChangeResult(
        from_value=from_val,
        to_value=to_val,
        pct_change=target_change.pct_change,
        fact_id_from=fact_from_id,
        fact_id_to=fact_to_id,
        classification=classification,
        cited_passages=cited_passages,
        all_fact_ids=all_fact_ids,
        semantic_results_count=len(raw_results),
        semantic_evidence_found=semantic_evidence_found,
        llm_explanation=answer_text,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _facts_to_data_points(facts: List[NormalizedFact]) -> List[DataPoint]:
    from app.services.analytics.analytics_service import _label
    return [
        DataPoint(
            period_label=f.period_label or _label(f),
            period_start=f.period_start,
            period_end=f.period_end,
            value=f.normalized_value,
            fact_id=f.id,
        )
        for f in facts
        if f.normalized_value is not None
    ]


def _find_target_change(
    changes: List[YoYChange],
    data_points: List[DataPoint],
    period_year: int,
) -> Optional[YoYChange]:
    """Return the YoY change where the 'to_period' most closely matches period_year."""
    if not changes:
        return None

    # Find data points in the target year
    year_points = [
        dp for dp in data_points
        if dp.period_start is not None and dp.period_start.year <= period_year <= (
            dp.period_end.year if dp.period_end else dp.period_start.year
        )
    ]

    if not year_points:
        # Fall back to the last available change
        return changes[-1]

    target_label = year_points[0].period_label
    for change in reversed(changes):
        if change.to_period == target_label or change.from_period == target_label:
            return change

    return changes[-1]


def _get_values_from_change(
    change: YoYChange,
    data_points: List[DataPoint],
) -> tuple[Optional[float], Optional[float]]:
    """Extract from_value / to_value from a YoYChange using data_points."""
    by_label = {dp.period_label: dp.value for dp in data_points}
    return by_label.get(change.from_period), by_label.get(change.to_period)


def _build_passages(raw_results: list[dict]) -> list[dict]:
    """Normalise Qdrant results into a passage list for the LLM prompt."""
    return [
        {
            "index": i,
            "document_id":       r.get("document_id", ""),
            "document_filename": r.get("document_filename", ""),
            "page_number":       r.get("page_number"),
            "excerpt":           r.get("text_excerpt", "")[:800],
        }
        for i, r in enumerate(raw_results)
    ]


async def _run_citation_llm(
    *,
    entity_name: str,
    metric: str,
    period_year: int,
    from_value: Optional[float],
    to_value: Optional[float],
    pct_change: Optional[float],
    passages: list[dict],
) -> dict:
    """Call the synthesis LLM (14b) with strict citation constraints.

    Returns the parsed JSON response dict. On gateway failure, returns a
    'insufficient-evidence' stub so the caller always gets a usable dict.
    """
    passages_text = "\n\n".join(
        f"[P{p['index']}] (Doc: {p['document_filename']}, Page: {p['page_number']})\n{p['excerpt']}"
        for p in passages
    )

    change_desc = (
        f"{from_value} → {to_value} "
        f"({'%.1f' % pct_change}% change)" if pct_change is not None else "unknown change"
    )

    system_prompt = (
        "You are a factual synthesizer for a coal mining analytics system. "
        "Your ONLY job is to find explicit, documented explanations in the provided passages.\n\n"
        "STRICT RULES:\n"
        "1. ONLY use content from the passages below. Do NOT add external knowledge.\n"
        "2. For EVERY explanatory claim, you MUST cite the passage index using [P0], [P1], etc.\n"
        "3. If no passage explicitly explains the change, set has_sufficient_evidence to false.\n"
        "4. Do NOT compute or modify any number — use only the change value given to you.\n"
        "5. Respond ONLY with valid JSON. No code fences. No explanation outside the JSON."
    )

    user_prompt = (
        f"Entity: {entity_name}\n"
        f"Metric: {metric.replace('_', ' ')}\n"
        f"Period: {period_year}\n"
        f"Observed change: {change_desc}\n\n"
        f"Retrieved passages:\n{passages_text}\n\n"
        "Return this JSON:\n"
        '{\n'
        '  "answer_text": "...",\n'
        '  "cited_passage_indices": [0, 2],\n'
        '  "has_sufficient_evidence": true,\n'
        '  "insufficient_evidence_reason": null\n'
        '}'
    )

    _schema = {
        "required": ["answer_text", "cited_passage_indices", "has_sufficient_evidence"],
        "properties": {
            "answer_text": {"type": "string"},
            "cited_passage_indices": {"type": "array"},
            "has_sufficient_evidence": {"type": "boolean"},
        },
    }

    try:
        result = await model_gateway.generate(
            prompt=user_prompt,
            role="synthesis",
            system=system_prompt,
            json_schema=_schema,
        )
        return result  # type: ignore[return-value]
    except model_gateway.ModelGatewayError as exc:
        logger.warning("Why-change LLM call failed: %s", exc)
        return {
            "answer_text": "",
            "cited_passage_indices": [],
            "has_sufficient_evidence": False,
            "insufficient_evidence_reason": str(exc),
        }


async def _check_data_derived(yoy_changes: List[YoYChange], metric: str) -> str:
    """Determine if a data-derived pattern exists (correlated changes) vs. truly insufficient.

    For Phase 3: if we have ≥2 consecutive YoY changes in the same direction,
    we classify as 'data-derived' (a trend pattern exists in the data).
    Otherwise: 'insufficient-evidence'.
    """
    if len(yoy_changes) < 2:
        return "insufficient-evidence"

    signs = [
        1 if (c.pct_change or 0) > 0 else (-1 if (c.pct_change or 0) < 0 else 0)
        for c in yoy_changes
    ]
    # Check if last 2 changes are in the same direction
    if len(signs) >= 2 and signs[-1] == signs[-2] and signs[-1] != 0:
        return "data-derived"

    return "insufficient-evidence"
