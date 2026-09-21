"""Report Service orchestrator — Phase 4.

Coordinates: assembler → narrative_generator → DB persistence → export on demand.
All timing is measured and stored; generation_time_seconds is always a real measurement.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.phase4 import GeneratedReport
from app.services.report.assembler import ReportContent, ReportScope, assemble_report
from app.services.report.narrative_generator import generate_narratives

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_report(
    *,
    db: AsyncSession,
    scope: ReportScope,
) -> GeneratedReport:
    """Generate a complete report and persist it. Returns the DB row."""
    report_id = uuid.uuid4()

    # Create a pending DB record so callers can poll status
    db_row = GeneratedReport(
        id=report_id,
        scope=scope.to_dict(),
        status="generating",
    )
    db.add(db_row)
    await db.commit()
    await db.refresh(db_row)

    t_start = time.monotonic()
    try:
        # 1. Assemble structured content (no LLM)
        content = await assemble_report(db=db, report_id=report_id, scope=scope)

        # 2. Generate narrative sections (LLM, grounded in content)
        content = await generate_narratives(content)

        elapsed = time.monotonic() - t_start
        content.generation_time_seconds = elapsed

        # 3. Persist
        db_row.status = "complete"
        db_row.content_snapshot = content.to_dict()
        db_row.generation_time_seconds = elapsed
        db_row.model_used = content.model_used
        await db.commit()
        await db.refresh(db_row)
        logger.info("Report %s generated in %.1fs", report_id, elapsed)

    except Exception as exc:
        logger.exception("Report generation failed for %s: %s", report_id, exc)
        db_row.status = "failed"
        db_row.error = str(exc)
        await db.commit()
        raise

    return db_row


async def export_report(
    *,
    db: AsyncSession,
    report_id: uuid.UUID,
    fmt: str,
) -> Path:
    """Export a previously generated report to PDF/DOCX/XLSX. Returns the file path."""
    if fmt not in ("pdf", "docx", "xlsx"):
        raise ValueError(f"Unknown export format: {fmt!r}. Must be pdf, docx, or xlsx.")

    row = await db.get(GeneratedReport, report_id)
    if not row:
        raise FileNotFoundError(f"Report {report_id} not found.")
    if row.status != "complete":
        raise RuntimeError(f"Report {report_id} is not complete (status={row.status!r}).")

    content = _deserialize_content(row.content_snapshot)
    out_dir = Path(settings.REPORT_STORAGE_ROOT) / str(report_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"report.{fmt}"

    if fmt == "pdf":
        from app.services.report.exporters.pdf_exporter import export_pdf
        await export_pdf(content, out_path)
    elif fmt == "docx":
        from app.services.report.exporters.docx_exporter import export_docx
        await export_docx(content, out_path)
    elif fmt == "xlsx":
        from app.services.report.exporters.xlsx_exporter import export_xlsx
        await export_xlsx(content, out_path)

    return out_path


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> Optional[GeneratedReport]:
    return await db.get(GeneratedReport, report_id)


async def list_reports(db: AsyncSession, page: int = 1, page_size: int = 20):
    from sqlalchemy import func
    total_res = await db.execute(
        select(func.count()).select_from(GeneratedReport)
    )
    total = total_res.scalar_one()
    result = await db.execute(
        select(GeneratedReport)
        .order_by(GeneratedReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all(), total


def _deserialize_content(snapshot: dict) -> ReportContent:
    """Reconstruct a ReportContent from its persisted JSON snapshot."""
    from datetime import date, datetime
    from app.services.report.assembler import (
        Citation, NarrativeSection, TableSection, TrendSection,
        DataPoint, SeriesData, WarningsSection, ReportScope,
    )

    scope_d = snapshot["scope"]
    scope = ReportScope(
        entity_ids=None,
        metrics=scope_d.get("metrics"),
        period_start=date.fromisoformat(scope_d["period_start"]),
        period_end=date.fromisoformat(scope_d["period_end"]),
        label=scope_d.get("label", ""),
    )

    def _narrative(d) -> NarrativeSection:
        return NarrativeSection(heading=d["heading"], text=d.get("text",""), citation_keys=d.get("citation_keys",[]))

    def _table(d) -> TableSection:
        return TableSection(heading=d["heading"], rows=d.get("rows",[]))

    def _trends(d) -> TrendSection:
        series = []
        for s in d.get("series", []):
            dps = [DataPoint(
                period_label=dp["period_label"],
                period_start=date.fromisoformat(dp["period_start"]) if dp.get("period_start") else None,
                period_end  =date.fromisoformat(dp["period_end"])   if dp.get("period_end")   else None,
                value=dp.get("value"),
                fact_id=uuid.UUID(dp["fact_id"]) if dp.get("fact_id") else None,
                has_conflict=dp.get("has_conflict", False),
                citation_key=dp.get("citation_key"),
            ) for dp in s.get("data_points", [])]
            series.append(SeriesData(
                entity_name=s["entity_name"], metric=s["metric"], unit=s.get("unit"), data_points=dps
            ))
        return TrendSection(heading=d["heading"], series=series)

    def _warnings(d) -> WarningsSection:
        return WarningsSection(
            heading=d["heading"],
            open_flags=d.get("open_flags",[]),
            open_conflicts=d.get("open_conflicts",[]),
        )

    citations = [
        Citation(
            claim_key=c["claim_key"],
            normalized_fact_id=uuid.UUID(c["normalized_fact_id"]),
            document_id=uuid.UUID(c["document_id"]),
            document_filename=c["document_filename"],
            page_number=c.get("page_number"),
            excerpt=c.get("excerpt",""),
            extraction_confidence=c.get("extraction_confidence"),
        )
        for c in snapshot.get("citations", [])
    ]

    rec_d = snapshot.get("recommendations")
    return ReportContent(
        report_id=uuid.UUID(snapshot["report_id"]),
        generated_at=datetime.fromisoformat(snapshot["generated_at"]),
        scope=scope,
        executive_summary=_narrative(snapshot["executive_summary"]),
        production_overview=_table(snapshot["production_overview"]),
        historical_trends=_trends(snapshot["historical_trends"]),
        comparative_analysis=_table(snapshot["comparative_analysis"]),
        data_quality_warnings=_warnings(snapshot["data_quality_warnings"]),
        recommendations=_narrative(rec_d) if rec_d else None,
        citations=citations,
        dq_warning_count=snapshot.get("dq_warning_count", 0),
        generation_time_seconds=snapshot.get("generation_time_seconds", 0.0),
        model_used=snapshot.get("model_used", ""),
    )
