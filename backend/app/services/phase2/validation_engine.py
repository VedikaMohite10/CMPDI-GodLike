"""Validation engine — deterministic checks producing ValidationFlag rows.

All 7 flag types from the design plan:
  1. missing_entity       — entity_resolution = 'unresolved'
  2. missing_unit         — normalized_unit is None AND raw_unit_text was present
  3. missing_date         — period_start is None AND raw_date_text was present
  4. ocr_anomaly          — heuristic checks for likely OCR transcription errors
  5. out_of_range         — value outside configured bounds for metric
  6. historical_deviation — >N% deviation from prior period for same entity/metric
  7. low_confidence       — extraction_confidence below threshold
  8. incomplete_row       — table row with one or more required cells blank
"""
import logging
import math
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase2 import NormalizedFact, ExtractedFact, ValidationFlag
from app.services.phase2.metric_registry import METRIC_RANGES

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD    = 0.4
HISTORICAL_DEVIATION_PCT    = 30.0   # flag if value deviates >30% from prior period


async def run_all_checks(
    nf: NormalizedFact, ef: ExtractedFact, db: AsyncSession
) -> list[ValidationFlag]:
    """Run all validation checks; return list of un-persisted ValidationFlag rows."""
    flags: list[ValidationFlag] = []

    flags.extend(_check_missing_entity(nf))
    flags.extend(_check_missing_unit(nf, ef))
    flags.extend(_check_missing_date(nf, ef))
    flags.extend(_check_low_confidence(nf, ef))
    flags.extend(_check_ocr_anomaly(nf, ef))
    flags.extend(_check_out_of_range(nf))
    flags.extend(await _check_historical_deviation(nf, db))

    return flags


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _flag(nf: NormalizedFact, flag_type: str, severity: str, detail: dict) -> ValidationFlag:
    return ValidationFlag(
        normalized_fact_id=nf.id,
        flag_type=flag_type,
        severity=severity,
        detail=detail,
        status="open",
    )


def _check_missing_entity(nf: NormalizedFact) -> list[ValidationFlag]:
    if nf.entity_resolution_method == "unresolved" or nf.canonical_entity_id is None:
        return [_flag(nf, "missing_entity", "warning", {
            "raw_entity_text": nf.extracted_fact.raw_entity_text if nf.extracted_fact else None,
            "note": "Could not resolve entity to any canonical entry",
        })]
    return []


def _check_missing_unit(nf: NormalizedFact, ef: ExtractedFact) -> list[ValidationFlag]:
    # Flag if unit is None AND the metric is one that normally has a unit
    metrics_requiring_unit = {"coal_production", "coal_dispatch", "ob_removal",
                               "seam_depth", "seam_thickness"}
    if nf.metric in metrics_requiring_unit and nf.normalized_unit is None:
        return [_flag(nf, "missing_unit", "warning", {
            "metric": nf.metric,
            "raw_unit_text": ef.raw_unit_text,
            "note": "Unit missing or unrecognized for a metric that requires one",
        })]
    return []


def _check_missing_date(nf: NormalizedFact, ef: ExtractedFact) -> list[ValidationFlag]:
    if nf.period_start is None and ef.raw_date_text:
        return [_flag(nf, "missing_date", "info", {
            "raw_date_text": ef.raw_date_text,
            "parse_method": nf.date_parse_method,
            "note": "Date text present but could not be parsed",
        })]
    return []


def _check_low_confidence(nf: NormalizedFact, ef: ExtractedFact) -> list[ValidationFlag]:
    conf = ef.extraction_confidence
    if conf is not None and conf < LOW_CONFIDENCE_THRESHOLD:
        return [_flag(nf, "low_confidence", "info", {
            "extraction_confidence": conf,
            "threshold": LOW_CONFIDENCE_THRESHOLD,
            "extraction_method": ef.extraction_method,
        })]
    return []


def _check_ocr_anomaly(nf: NormalizedFact, ef: ExtractedFact) -> list[ValidationFlag]:
    """Heuristic OCR error detection.

    Checks:
    - Implausible decimal shift: if normalized_value is ~1000× expected range lower bound
      but raw_value with "." removed would be in range → likely missing decimal
    - Non-numeric characters embedded in raw_value (e.g. "l5.4" instead of "15.4")
    """
    flags = []
    raw = ef.raw_value or ""
    norm_v = nf.normalized_value

    # 1. Non-digit/non-punctuation characters that suggest OCR confusion
    import re
    ocr_suspect_chars = re.findall(r"[a-zA-Z]", raw)
    if ocr_suspect_chars and norm_v is None:
        flags.append(_flag(nf, "ocr_anomaly", "warning", {
            "raw_value": raw,
            "suspect_chars": ocr_suspect_chars,
            "note": "Raw value contains alpha chars — possible OCR confusion (e.g. 'l' for '1')",
        }))

    # 2. Decimal shift: value × 1000 would be in plausible range but raw value is not
    if norm_v is not None and nf.metric and nf.metric in METRIC_RANGES:
        lo, hi = METRIC_RANGES[nf.metric]
        if lo is not None and hi is not None:
            if norm_v < lo and (norm_v * 1000) <= hi:
                flags.append(_flag(nf, "ocr_anomaly", "warning", {
                    "raw_value": raw,
                    "normalized_value": norm_v,
                    "plausible_range": [lo, hi],
                    "note": "Value may have a missing decimal point (×1000 would be in range)",
                }))
            elif norm_v > hi and (norm_v / 1000) >= lo:
                flags.append(_flag(nf, "ocr_anomaly", "warning", {
                    "raw_value": raw,
                    "normalized_value": norm_v,
                    "plausible_range": [lo, hi],
                    "note": "Value may have an extra zero (÷1000 would be in range)",
                }))

    return flags


def _check_out_of_range(nf: NormalizedFact) -> list[ValidationFlag]:
    if nf.normalized_value is None or not nf.metric:
        return []
    bounds = METRIC_RANGES.get(nf.metric)
    if bounds is None:
        return []
    lo, hi = bounds
    v = nf.normalized_value
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        return [_flag(nf, "out_of_range", "warning", {
            "metric": nf.metric,
            "normalized_value": v,
            "normalized_unit": nf.normalized_unit,
            "plausible_range": [lo, hi],
            "note": "Value outside expected plausible range for this metric",
        })]
    return []


async def _check_historical_deviation(
    nf: NormalizedFact, db: AsyncSession
) -> list[ValidationFlag]:
    """Flag if value deviates >HISTORICAL_DEVIATION_PCT from same entity/metric prior periods."""
    if not all([nf.canonical_entity_id, nf.metric, nf.period_start,
                nf.normalized_value, nf.normalized_unit]):
        return []

    # Fetch prior normalized facts for same entity+metric (excluding current)
    result = await db.execute(
        select(NormalizedFact.normalized_value, NormalizedFact.period_start)
        .where(
            and_(
                NormalizedFact.canonical_entity_id == nf.canonical_entity_id,
                NormalizedFact.metric == nf.metric,
                NormalizedFact.normalized_unit == nf.normalized_unit,
                NormalizedFact.normalized_value.is_not(None),
                NormalizedFact.period_start < nf.period_start,
                NormalizedFact.id != nf.id,
            )
        )
        .order_by(NormalizedFact.period_start.desc())
        .limit(3)
    )
    prior_rows = result.all()
    if not prior_rows:
        return []

    avg_prior = sum(r.normalized_value for r in prior_rows) / len(prior_rows)
    if avg_prior == 0:
        return []

    delta_pct = abs(nf.normalized_value - avg_prior) / avg_prior * 100
    if delta_pct > HISTORICAL_DEVIATION_PCT:
        return [_flag(nf, "historical_deviation", "info", {
            "metric": nf.metric,
            "current_value": nf.normalized_value,
            "avg_prior_value": round(avg_prior, 4),
            "prior_periods_used": len(prior_rows),
            "delta_pct": round(delta_pct, 2),
            "threshold_pct": HISTORICAL_DEVIATION_PCT,
            "note": "Current value deviates significantly from prior period average",
        })]
    return []
