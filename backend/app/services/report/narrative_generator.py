"""Narrative Generator — Phase 4.

Generates LLM-authored prose sections (Executive Summary, Findings, Recommendations)
STRICTLY grounded in the structured data already assembled by assembler.py.

Design rules enforced by this module:
  1. The LLM receives ONLY the structured section data (tables, trends, warnings).
     It is NEVER given free latitude to add new facts, entities, or figures.
  2. The system prompt explicitly prohibits adding any number, entity name, or
     date not already present in the provided structured data.
  3. Each generated narrative records which model was used in the report header.
  4. If the LLM call fails, the narrative falls back to a deterministic template
     so the report is still complete and exportable.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.config import get_settings
from app.services import model_gateway
from app.services.report.assembler import NarrativeSection, ReportContent

logger = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM_PROMPT = """You are a technical report writer for a coal mining intelligence system.
You will receive structured data extracted from official mining documents.
Your task is to write a concise, professional narrative section summarising ONLY what is in the data provided.

STRICT RULES:
- Do NOT add any numbers, percentages, dates, entity names, or figures that are not explicitly present in the structured data below.
- Do NOT speculate about causes, forecasts, or implications beyond what the data directly shows.
- Write in third person, past tense, formal register.
- Maximum length: 3–4 paragraphs.
- Do not mention "AI", "model", "LLM", or "this report was generated".
"""


async def generate_narratives(content: ReportContent) -> ReportContent:
    """Fill .text fields on narrative sections in-place. Returns the same object.

    Calls ModelGateway 'synthesis' role. Falls back gracefully if the model
    is unavailable or returns unusable output.
    """
    model = settings.SYNTHESIS_LLM_MODEL

    # --- Executive Summary ---
    content.executive_summary.text = await _generate_section(
        heading="Executive Summary",
        structured_data={
            "scope":             content.scope.to_dict(),
            "production_overview": content.production_overview.to_dict(),
            "trend_series_count": len(content.historical_trends.series),
            "dq_warning_count":  content.dq_warning_count,
        },
        instruction=(
            "Write an executive summary covering the reporting period, "
            "key production figures, and any data quality warnings. "
            "Do not add any new figures."
        ),
    )

    # --- Recommendations (only if section exists) ---
    if content.recommendations is not None:
        anomaly_rows = [
            row for s in content.historical_trends.series
            for dp in s.data_points
            if dp.has_conflict
        ]
        content.recommendations.text = await _generate_section(
            heading="Recommendations",
            structured_data={
                "open_conflicts": content.data_quality_warnings.open_conflicts,
                "conflicting_data_points_count": len(anomaly_rows),
                "open_flags_count": len(content.data_quality_warnings.open_flags),
            },
            instruction=(
                "Based ONLY on the data quality issues listed, write brief "
                "recommendations for resolving them. Do not invent new recommendations."
            ),
        )

    content.model_used = model
    return content


async def _generate_section(
    heading: str,
    structured_data: dict,
    instruction: str,
) -> str:
    """Call the synthesis LLM to generate one narrative section."""
    user_prompt = (
        f"Section: {heading}\n\n"
        f"Instruction: {instruction}\n\n"
        f"Structured data (JSON):\n"
        f"{json.dumps(structured_data, indent=2, default=str)}\n\n"
        f"Write the narrative section now. Output plain text only — no JSON, no markdown."
    )
    try:
        text = await model_gateway.generate(
            prompt=user_prompt,
            role="synthesis",
            system=_SYSTEM_PROMPT,
        )
        if isinstance(text, dict):
            # Should not happen for role=synthesis with no json_schema, but guard anyway
            text = json.dumps(text)
        return str(text).strip()
    except Exception as exc:
        logger.warning("Narrative generation failed for section '%s': %s", heading, exc)
        return _fallback_narrative(heading, structured_data)


def _fallback_narrative(heading: str, structured_data: dict) -> str:
    """Deterministic fallback when the LLM call fails."""
    n_rows = len(structured_data.get("production_overview", {}).get("rows", []))
    n_warnings = structured_data.get("dq_warning_count", 0)
    return (
        f"{heading}: This section summarises {n_rows} production data points "
        f"across the reporting period. "
        f"{n_warnings} data quality warning(s) were identified and are detailed in the "
        f"Data Quality Warnings section. Narrative generation was unavailable; "
        f"please refer to the structured tables for full detail."
    )
