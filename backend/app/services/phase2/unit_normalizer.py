"""Unit normalizer — deterministic, no LLM.

Converts raw unit strings and raw value strings to canonical (unit, value) pairs.
All conversion rules are in metric_registry.py.
"""
import re
from typing import Optional

from app.services.phase2.metric_registry import resolve_unit


_NUMERIC_RE = re.compile(r"^[+-]?\s*(\d[\d,]*\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def parse_numeric(raw_value: str) -> Optional[float]:
    """Parse a raw cell string to float. Returns None if unparseable.

    Handles: comma thousand-separators, leading/trailing whitespace, parentheses
    for negatives (e.g. "(5.2)"), and simple percentages (stripped of %).
    """
    if not raw_value:
        return None
    s = raw_value.strip()
    # Remove surrounding parens → negative
    negative = False
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
        negative = True
    # Strip trailing % (treat as dimensionless number; unit handled separately)
    if s.endswith("%"):
        s = s[:-1].strip()
    # Remove thousand-separators
    s = s.replace(",", "")
    if not _NUMERIC_RE.match(s):
        return None
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def normalize_unit(
    raw_value: str, raw_unit: Optional[str]
) -> tuple[Optional[float], Optional[str], Optional[str], dict]:
    """Normalize a (raw_value, raw_unit) pair.

    Returns:
        (normalized_value, normalized_unit, conversion_note, notes_dict)

    If the unit is unrecognized, returns (numeric, None, None, notes) —
    the caller stores raw_unit_text and flags it.
    """
    numeric = parse_numeric(raw_value)
    notes: dict = {}

    if numeric is None:
        notes["parse_error"] = f"Could not parse numeric from {raw_value!r}"
        return None, None, None, notes

    if not raw_unit:
        notes["unit_missing"] = True
        return numeric, None, None, notes

    result = resolve_unit(raw_unit)
    if result is None:
        notes["unit_unrecognized"] = raw_unit
        return numeric, None, None, notes

    canonical_unit, factor = result
    normalized_value = numeric * factor

    if factor != 1.0:
        notes["unit_conversion"] = f"{raw_unit}→{canonical_unit} ×{factor}"

    return normalized_value, canonical_unit, f"{raw_unit}→{canonical_unit}", notes
