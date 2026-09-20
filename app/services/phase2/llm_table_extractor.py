"""LLM-based table fact extractor using qwen2.5:7b-instruct.

Design decisions:
- Strict JSON schema prompt — no prose, no markdown fences in response
- Max 2 retries on JSON parse failure (same prompt, cheaper than 14b fallback)
- On 3rd failure: store raw output, emit low_confidence flag, return []
- Merged-cell / mismatched-column-count tables → skip + flag immediately
- Model is configurable via FACT_LLM_MODEL env var (default: 7b)
"""
import json
import logging
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_RETRIES   = 2
_CONTEXT_CHARS = 300


async def _ollama_chat(model: str, messages: list[dict]) -> str:
    """Call Ollama /api/chat and return the assistant message content."""
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {"model": model, "stream": False, "messages": messages,
               "options": {"temperature": 0.0, "num_predict": 2048}}
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Pydantic schema for LLM JSON output — deterministically parseable
# ---------------------------------------------------------------------------
class FactItem(BaseModel):
    row_index:    int
    entity_text:  Optional[str] = None
    metric_text:  str
    value_text:   str
    unit_text:    Optional[str] = None
    date_text:    Optional[str] = None
    confidence:   float = 0.5


class LLMTableResponse(BaseModel):
    facts:        list[FactItem] = []
    table_skipped: bool          = False
    skip_reason:  Optional[str]  = None


# ---------------------------------------------------------------------------
# System prompt (sent once per call)
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a structured data extractor for Indian coal mining reports.
Your job: given a table with headers and rows, extract ONLY explicitly stated numerical facts.
Do NOT calculate, infer, or estimate values not present in the table.
Do NOT fill in missing cells.
Return ONLY a JSON object matching this exact schema — no markdown, no explanation:

{
  "facts": [
    {
      "row_index": <int>,
      "entity_text": <str or null>,
      "metric_text": <str>,
      "value_text": <str>,
      "unit_text": <str or null>,
      "date_text": <str or null>,
      "confidence": <float 0.0-1.0>
    }
  ],
  "table_skipped": <bool>,
  "skip_reason": <str or null>
}

Rules:
- entity_text: the row-label (mine name, location, subsidiary) — null if the table has no entity column
- metric_text: the column header describing the value
- value_text: the raw cell value exactly as it appears — DO NOT convert units
- unit_text: unit from the column header or cell (e.g. "MT", "MCM", "m"), null if absent
- date_text: reporting period from header or caption, null if not discernible
- confidence: 1.0 = clearly a numeric production/survey fact; 0.0 = very uncertain
- Set table_skipped=true ONLY if the table contains no numeric production/survey data at all
"""


def _build_user_message(
    caption: str,
    context: str,
    headers: list[str],
    rows: list[list[str]],
) -> str:
    return (
        f"Table caption: {caption or '(none)'}\n"
        f"Context: {context[:_CONTEXT_CHARS] or '(none)'}\n"
        f"Headers: {json.dumps(headers)}\n"
        f"Rows:\n{json.dumps(rows, ensure_ascii=False)}\n\n"
        "Extract all numeric production/survey facts from this table."
    )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that some models add despite instructions."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def extract_facts_from_table(
    caption: str,
    context: str,
    headers: list[str],
    rows: list[list[str]],
    table_id: str = "",
) -> tuple[list[FactItem], dict[str, Any], bool]:
    """Call LLM to extract facts from one table.

    Returns:
        (parsed_facts, raw_llm_output_dict, was_skipped)

    raw_llm_output_dict always contains the last LLM response for audit storage.
    If all retries fail, returns ([], {"error": ...}, False).
    """
    # Pre-flight: skip table if column count inconsistent (merged-cell signal)
    if rows:
        col_counts = {len(r) for r in rows}
        col_counts.add(len(headers))
        if len(col_counts) > 1:
            logger.warning(
                "Table %s has inconsistent column counts %s — skipping LLM extraction.",
                table_id, col_counts,
            )
            return [], {"table_skipped": True, "skip_reason": "inconsistent_column_counts"}, True

    user_msg = _build_user_message(caption, context, headers, rows)
    model    = getattr(settings, "FACT_LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M")
    raw_out: dict = {}

    for attempt in range(_MAX_RETRIES + 1):
        try:
            raw_text = await _ollama_chat(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
            )
            raw_out  = {"raw_text": raw_text, "attempt": attempt + 1}

            cleaned  = _strip_fences(raw_text)
            parsed   = json.loads(cleaned)
            result   = LLMTableResponse(**parsed)

            raw_out["parsed"] = result.model_dump()
            if result.table_skipped:
                return [], raw_out, True
            return result.facts, raw_out, False

        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            logger.warning(
                "LLM table extraction attempt %d/%d failed for table %s: %s",
                attempt + 1, _MAX_RETRIES + 1, table_id, exc,
            )
            raw_out["parse_error"] = str(exc)
            if attempt == _MAX_RETRIES:
                raw_out["all_retries_failed"] = True
                return [], raw_out, False

        except Exception as exc:
            logger.error("LLM call failed for table %s: %s", table_id, exc)
            raw_out["llm_error"] = str(exc)
            return [], raw_out, False

    return [], raw_out, False
