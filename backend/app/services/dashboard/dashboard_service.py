"""Data Quality Dashboard Service — Phase 4.

All numbers are computed LIVE from actual DB data. No hard-coded placeholders.
If a metric cannot be reliably computed, it returns null/None with a note
(see PerformanceStats.note_on_nulls).

Automation percentage definition (approved in Phase 4 plan):
  automation_pct = (total_active_facts - human_corrected_facts) / total_active_facts * 100

  Where:
    total_active_facts     = NormalizedFacts with fact_processing_status != 'rejected'
    human_corrected_facts  = NormalizedFacts with at least one audit_log entry
                             where action_type = 'correct' AND target_table = 'normalized_facts'

  CAVEAT: automation_pct is returned alongside review_coverage_pct and an
  explicit caveat string so consumers understand the denominator's reliability.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.extraction import ExtractedTable, ExtractedTextBlock
from app.models.page import Page
from app.models.phase2 import (
    Conflict, DuplicateCandidate, ExtractedFact, NormalizedFact, ValidationFlag,
)
from app.models.phase4 import AuditLog, GeneratedReport
from app.models.phase5 import BenchmarkRun

logger = logging.getLogger(__name__)


async def compute_dashboard_stats(db: AsyncSession) -> dict:
    """Compute and return all dashboard metrics from live DB data."""
    now = datetime.now(timezone.utc)

    pipeline     = await _pipeline_stats(db)
    extraction   = await _extraction_stats(db)
    trust        = await _trust_stats(db)
    normalization = await _normalization_stats(db)
    review       = await _review_stats(db)
    automation   = _compute_automation(review)
    performance  = await _performance_stats(db)
    benchmark    = await _benchmark_stats(db)

    return {
        "computed_at":    now.isoformat(),
        "pipeline":       pipeline,
        "extraction":     extraction,
        "trust":          trust,
        "normalization":  normalization,
        "review":         review,
        "automation":     automation,
        "performance":    performance,
        "benchmark":      benchmark,
    }


# ---------------------------------------------------------------------------
# Sub-stat builders
# ---------------------------------------------------------------------------

async def _pipeline_stats(db: AsyncSession) -> dict:
    docs_processed = (await db.execute(
        select(func.count()).select_from(Document)
        .where(Document.processing_status == "complete")
    )).scalar_one()

    pages_processed = (await db.execute(
        select(func.count()).select_from(Page)
        .join(Document, Document.id == Page.document_id)
        .where(Document.processing_status == "complete")
    )).scalar_one()

    tables_extracted = (await db.execute(
        select(func.count()).select_from(ExtractedTable)
    )).scalar_one()

    text_blocks = (await db.execute(
        select(func.count()).select_from(ExtractedTextBlock)
    )).scalar_one()

    return {
        "documents_processed":   docs_processed,
        "pages_processed":       pages_processed,
        "tables_extracted":      tables_extracted,
        "text_blocks_extracted": text_blocks,
    }


async def _extraction_stats(db: AsyncSession) -> dict:
    total_facts = (await db.execute(
        select(func.count()).select_from(ExtractedFact)
    )).scalar_one()

    avg_conf = (await db.execute(
        select(func.avg(ExtractedFact.extraction_confidence))
        .where(ExtractedFact.extraction_confidence.isnot(None))
    )).scalar_one()

    high = (await db.execute(
        select(func.count()).select_from(ExtractedFact)
        .where(ExtractedFact.extraction_confidence > 0.8)
    )).scalar_one()

    medium = (await db.execute(
        select(func.count()).select_from(ExtractedFact)
        .where(and_(
            ExtractedFact.extraction_confidence >= 0.5,
            ExtractedFact.extraction_confidence <= 0.8,
        ))
    )).scalar_one()

    low = (await db.execute(
        select(func.count()).select_from(ExtractedFact)
        .where(ExtractedFact.extraction_confidence < 0.5)
    )).scalar_one()

    return {
        "total_extracted_facts": total_facts,
        "confidence_distribution": {
            "high_gt_0_8":       high,
            "medium_0_5_to_0_8": medium,
            "low_lt_0_5":        low,
        },
        "low_confidence_fact_count": low,
        "avg_extraction_confidence": round(float(avg_conf), 4) if avg_conf else None,
    }


async def _trust_stats(db: AsyncSession) -> dict:
    open_conflicts = (await db.execute(
        select(func.count()).select_from(Conflict)
        .where(Conflict.status == "open")
    )).scalar_one()

    resolved_conflicts = (await db.execute(
        select(func.count()).select_from(Conflict)
        .where(Conflict.status == "resolved")
    )).scalar_one()

    missing_flags = (await db.execute(
        select(func.count()).select_from(ValidationFlag)
        .where(and_(
            ValidationFlag.flag_type == "missing_value",
            ValidationFlag.status == "open",
        ))
    )).scalar_one()

    dup_open = (await db.execute(
        select(func.count()).select_from(DuplicateCandidate)
        .where(DuplicateCandidate.status == "open")
    )).scalar_one()

    return {
        "open_conflicts":            open_conflicts,
        "resolved_conflicts":        resolved_conflicts,
        "missing_value_flags":       missing_flags,
        "duplicate_candidates_open": dup_open,
    }


async def _normalization_stats(db: AsyncSession) -> dict:
    total_nf = (await db.execute(
        select(func.count()).select_from(NormalizedFact)
    )).scalar_one()

    # Facts that have at least one open flag
    flagged = (await db.execute(
        select(func.count(NormalizedFact.id.distinct()))
        .join(ValidationFlag, ValidationFlag.normalized_fact_id == NormalizedFact.id)
        .where(ValidationFlag.status == "open")
    )).scalar_one()

    return {
        "total_normalized_facts": total_nf,
        "facts_with_open_flags":  flagged,
    }


async def _review_stats(db: AsyncSession) -> dict:
    # Total correction events (useful for audit volume; NOT used in automation formula)
    correction_events = (await db.execute(
        select(func.count()).select_from(AuditLog)
        .where(and_(
            AuditLog.action_type == "correct",
            AuditLog.target_table == "normalized_facts",
        ))
    )).scalar_one()

    # Distinct facts that have been corrected at least once
    # Used in the automation formula: a fact corrected N times still counts as 1 corrected fact.
    distinct_corrected_res = await db.execute(
        select(func.count(AuditLog.target_id.distinct()))
        .where(and_(
            AuditLog.action_type == "correct",
            AuditLog.target_table == "normalized_facts",
        ))
    )
    distinct_corrected_facts = distinct_corrected_res.scalar_one()

    accepts = (await db.execute(
        select(func.count()).select_from(AuditLog)
        .where(AuditLog.action_type == "accept")
    )).scalar_one()

    rejects = (await db.execute(
        select(func.count()).select_from(AuditLog)
        .where(AuditLog.action_type == "reject")
    )).scalar_one()

    # total_active_facts: not rejected
    total_active = (await db.execute(
        select(func.count()).select_from(NormalizedFact)
        .where(NormalizedFact.fact_processing_status != "rejected")
    )).scalar_one()

    # Reviewed = facts that have any audit log action targeting normalized_facts
    reviewed_fact_ids = (await db.execute(
        select(AuditLog.target_id.distinct())
        .where(AuditLog.target_table == "normalized_facts")
    )).scalars().all()
    total_reviewed = len(reviewed_fact_ids)
    unreviewed = max(0, total_active - total_reviewed)
    coverage_pct = round(total_reviewed / total_active * 100, 2) if total_active > 0 else 0.0

    return {
        "human_corrections_count":        correction_events,       # audit volume (raw events)
        "distinct_corrected_facts_count": distinct_corrected_facts, # used in automation formula
        "human_accepts_count":            accepts,
        "human_rejects_count":            rejects,
        "total_reviewed_facts":           total_reviewed,
        "total_active_facts":             total_active,
        "unreviewed_facts":               unreviewed,
        "review_coverage_pct":            coverage_pct,
    }


def _compute_automation(review: dict) -> dict:
    total_active         = review["total_active_facts"]
    # Use distinct corrected facts (not raw event count) to avoid double-counting
    # facts that were corrected multiple times.
    corrected_facts      = review["distinct_corrected_facts_count"]
    coverage_pct         = review["review_coverage_pct"]

    if total_active == 0:
        return {
            "automation_pct":        None,
            "formula":               "(total_active_facts - distinct_corrected_facts) / total_active_facts × 100",
            "numerator":             None,
            "denominator":           None,
            "automation_pct_caveat": "No active facts in pipeline yet.",
            "review_coverage_pct":   0.0,
        }

    numerator  = total_active - corrected_facts
    automation = round(numerator / total_active * 100, 2)

    caveat = (
        f"Only {coverage_pct:.2f}% of active facts have been reviewed. "
        f"automation_pct reflects the fraction of facts NOT requiring human correction "
        f"(counting each corrected fact once, regardless of how many times it was corrected), "
        f"but {100 - coverage_pct:.2f}% of facts are unreviewed — their correctness "
        f"is unknown. Do not interpret this number as an overall accuracy guarantee."
    )

    return {
        "automation_pct":        automation,
        "formula":               "(total_active_facts - distinct_corrected_facts) / total_active_facts × 100",
        "numerator":             int(numerator),
        "denominator":           int(total_active),
        "automation_pct_caveat": caveat,
        "review_coverage_pct":   coverage_pct,
    }


async def _performance_stats(db: AsyncSession) -> dict:
    # Avg document ingestion time from Document-level timestamps (Phase 4).
    # These are set by the ingestion orchestrator for all documents processed
    # after migration 0004. Documents ingested before migration will have NULL
    # timestamps and are excluded from the average (correct behaviour).
    avg_doc_res = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Document.ingestion_completed_at) -
                func.extract("epoch", Document.ingestion_started_at)
            )
        )
        .where(and_(
            Document.ingestion_started_at.isnot(None),
            Document.ingestion_completed_at.isnot(None),
        ))
    )
    avg_doc = avg_doc_res.scalar_one()

    # Fallback: avg Phase-2 fact-processing time from FactProcessingLog.
    # This only covers Phase 2 normalisation, not the full ingestion pipeline.
    from app.models.phase2 import FactProcessingLog
    proc_time_res = await db.execute(
        select(
            func.avg(
                func.extract("epoch", FactProcessingLog.completed_at) -
                func.extract("epoch", FactProcessingLog.started_at)
            )
        )
        .where(and_(
            FactProcessingLog.started_at.isnot(None),
            FactProcessingLog.completed_at.isnot(None),
            FactProcessingLog.status == "complete",
        ))
    )
    avg_phase2 = proc_time_res.scalar_one()

    # Avg report generation time
    avg_report_res = await db.execute(
        select(func.avg(GeneratedReport.generation_time_seconds))
        .where(and_(
            GeneratedReport.status == "complete",
            GeneratedReport.generation_time_seconds.isnot(None),
        ))
    )
    avg_report = avg_report_res.scalar_one()

    return {
        # Preferred: full end-to-end ingestion time measured at document level
        "avg_document_ingestion_time_seconds":  round(float(avg_doc), 2)     if avg_doc    else None,
        # Supplementary: Phase-2-only processing time
        "avg_phase2_processing_time_seconds":   round(float(avg_phase2), 2)  if avg_phase2 else None,
        "avg_report_generation_time_seconds":   round(float(avg_report), 2)  if avg_report else None,
        "note_on_nulls": (
            "null values mean insufficient data is available to compute this metric reliably. "
            "avg_document_ingestion_time_seconds is null for documents ingested before "
            "the Phase 4 migration (which added ingestion timing to the documents table). "
            "avg_phase2_processing_time_seconds requires FactProcessingLog rows with both "
            "started_at and completed_at populated. "
            "avg_report_generation_time_seconds requires at least one completed report."
        ),
    }


async def _benchmark_stats(db: AsyncSession) -> dict:
    """Return a summary of the latest benchmark run for the dashboard.

    Design contract:
      - real and synthetic metrics are NEVER merged; they are always in separate keys.
      - If no benchmark run exists yet, returns {"available": false}.
      - synthetic_doc_ids is listed so the dashboard can display provenance labels.
    """
    latest = (
        await db.execute(
            select(BenchmarkRun)
            .where(BenchmarkRun.is_latest.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()

    if latest is None:
        # Fallback: try the most recent run (is_latest may not have been set yet)
        latest = (
            await db.execute(
                select(BenchmarkRun)
                .order_by(BenchmarkRun.run_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    if latest is None:
        return {
            "available": False,
            "note":      "No benchmark run has been executed yet. POST /benchmark/run to generate one.",
        }

    total_runs = (
        await db.execute(select(func.count()).select_from(BenchmarkRun))
    ).scalar_one()

    return {
        "available":               True,
        "latest_run_id":           str(latest.id),
        "latest_run_at":           latest.run_at.isoformat(),
        "document_count_real":     latest.document_count_real,
        "document_count_synthetic":latest.document_count_synthetic,
        "sample_size":             latest.sample_size,
        "run_note":                latest.run_note,
        # Real and synthetic are ALWAYS in separate keys — never aggregated.
        "real_metrics":            latest.results.get("real"),
        "synthetic_metrics":       latest.results.get("synthetic"),
        "synthetic_doc_ids":       latest.results.get("synthetic_doc_ids", []),
        "total_runs":              total_runs,
        "note": (
            "real_metrics and synthetic_metrics are computed from separate label sets "
            "and are never aggregated into a single accuracy number."
        ),
    }
