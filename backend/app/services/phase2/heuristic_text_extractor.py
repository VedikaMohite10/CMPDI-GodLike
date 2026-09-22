"""Heuristic text-block fact extractor — no LLM involved.

Uses regex patterns to find (metric, value, unit) tuples in prose text.
All matches are flagged extraction_confidence=0.5 (conservative).
extraction_method='heuristic_text'.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns: (compiled_regex, metric_key, unit_override_or_None)
# Group layout: group(1) = value, group(2) = unit (optional)
# Patterns allow [\s\S]{0,60} between keyword and number to handle prose.
# ---------------------------------------------------------------------------
_UNIT_PAT = r"(MT|KT|lakh\s+tonnes?|crore\s+tonnes?|million\s+tonnes?)"
_VOL_PAT  = r"(MCM|BCM|million\s+cubic\s+met(?:res|ers)?)"
_LEN_PAT  = r"(m|met(?:res?|ers?))"

_PATTERNS: list[tuple[re.Pattern, str, Optional[str]]] = [
    # coal_production — keyword then ≤40 chars then number then unit
    (re.compile(
        r"(?:total\s+)?(?:raw\s+)?coal\s+(?:production|output).{0,40}?([0-9]+\.?[0-9]*)\s*" + _UNIT_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "coal_production", None),

    # coal dispatch
    (re.compile(
        r"coal\s+desp?atch(?:ed)?.{0,40}?([0-9]+\.?[0-9]*)\s*" + _UNIT_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "coal_dispatch", None),
    (re.compile(
        r"(?:^|\s)desp?atch(?:ed)?.{0,30}?([0-9]+\.?[0-9]*)\s*" + _UNIT_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "coal_dispatch", None),

    # OB removal
    (re.compile(
        r"(?:overburden|OB)\s+removal.{0,40}?([0-9]+\.?[0-9]*)\s*" + _VOL_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "ob_removal", None),

    # seam depth
    (re.compile(
        r"(?:coal\s+seam\s+)?depth.{0,30}?([0-9]+\.?[0-9]*)\s*" + _LEN_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "seam_depth", None),

    # seam thickness
    (re.compile(
        r"(?:seam\s+)?thickness.{0,30}?([0-9]+\.?[0-9]*)\s*" + _LEN_PAT,
        re.IGNORECASE | re.DOTALL,
    ), "seam_thickness", None),

    # Standalone "15.4 MT" / "45.2 MCM" — fallback, lower confidence
    (re.compile(r"\b([0-9]+\.[0-9]+)\s*(MT|MCM)\b", re.IGNORECASE), "unknown", None),
]

_HEURISTIC_CONFIDENCE = 0.5
_UNKNOWN_CONFIDENCE   = 0.3   # for the standalone-number fallback


def extract_from_text(
    text: str,
    entity_text: Optional[str] = None,
    date_text: Optional[str] = None,
) -> list[dict]:
    """Return list of raw fact dicts extracted from a text block.

    Each dict matches the fields needed for ExtractedFact creation:
    {raw_entity_text, raw_metric_text, raw_value, raw_unit_text,
     raw_date_text, extraction_confidence}
    """
    if not text or not text.strip():
        return []

    results = []
    seen: set[tuple] = set()  # deduplicate (metric, value, unit)

    for pattern, metric_key, unit_override in _PATTERNS:
        for m in pattern.finditer(text):
            value_str = m.group(1).strip()
            unit_str  = (unit_override or (m.group(2).strip() if m.lastindex and m.lastindex >= 2 else None))
            conf      = _UNKNOWN_CONFIDENCE if metric_key == "unknown" else _HEURISTIC_CONFIDENCE
            # For known metrics, store the key; for unknown, store None
            metric_text = metric_key if metric_key != "unknown" else None

            key = (metric_key, value_str, unit_str)
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "raw_entity_text":       entity_text,
                "raw_metric_text":       metric_text,
                "raw_value":             value_str,
                "raw_unit_text":         unit_str,
                "raw_date_text":         date_text,
                "extraction_confidence": conf,
            })

    return results
