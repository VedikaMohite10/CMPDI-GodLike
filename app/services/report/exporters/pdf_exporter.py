"""PDF Exporter — Phase 4.

Renders a ReportContent to PDF using reportlab (self-hosted, no external API).
Charts are generated locally with matplotlib and embedded as PNG images.

All data comes from the passed-in ReportContent object — nothing is re-queried
or approximated here.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import List, Optional

from app.services.report.assembler import ReportContent

logger = logging.getLogger(__name__)

# Lazy imports — only load reportlab/matplotlib when an export is actually requested
def _get_reportlab():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            Image as RLImage, HRFlowable,
        )
        return colors, A4, getSampleStyleSheet, ParagraphStyle, cm, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, RLImage, HRFlowable
    except ImportError as exc:
        raise RuntimeError(
            "reportlab is required for PDF export. Install with: pip install reportlab"
        ) from exc


def _build_chart(series_list, title: str) -> Optional[bytes]:
    """Render a time-series line chart with matplotlib. Returns PNG bytes or None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 3.5))
        has_data = False
        for s in series_list:
            xs = [dp.period_label for dp in s.data_points if dp.value is not None]
            ys = [dp.value for dp in s.data_points if dp.value is not None]
            if xs and ys:
                ax.plot(xs, ys, marker="o", label=s.entity_name)
                has_data = True

        if not has_data:
            plt.close(fig)
            return None

        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Period")
        unit_label = series_list[0].unit if series_list else ""
        ax.set_ylabel(unit_label or "Value")
        ax.legend(fontsize=7)
        plt.xticks(rotation=30, fontsize=7)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as exc:
        logger.warning("Chart generation failed: %s", exc)
        return None


async def export_pdf(content: ReportContent, output_path: Path) -> None:
    """Render the ReportContent to a PDF file at output_path."""
    colors, A4, getSampleStyleSheet, ParagraphStyle, cm, SimpleDocTemplate, \
        Paragraph, Spacer, Table, TableStyle, RLImage, HRFlowable = _get_reportlab()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=7, leading=9)

    story = []

    # --- Title ---
    story.append(Paragraph(f"Mining Intelligence Report", h1))
    story.append(Paragraph(f"Scope: {content.scope.label}", normal))
    story.append(Paragraph(
        f"Period: {content.scope.period_start} to {content.scope.period_end}", normal
    ))
    story.append(Paragraph(f"Generated: {content.generated_at.strftime('%Y-%m-%d %H:%M UTC')}", small))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Spacer(1, 0.3*cm))

    # --- Executive Summary ---
    _add_narrative(story, content.executive_summary.heading, content.executive_summary.text, h2, normal)

    # --- Production Overview Table ---
    story.append(Paragraph(content.production_overview.heading, h2))
    if content.production_overview.rows:
        headers = ["Entity", "Metric", "Period", "Value", "Unit", "Citation"]
        table_data = [headers]
        for row in content.production_overview.rows:
            table_data.append([
                str(row.get("entity", "")),
                str(row.get("metric", "")),
                str(row.get("period", "")),
                str(row.get("value", "")),
                str(row.get("unit", "")),
                str(row.get("citation_key", "")),
            ])
        t = Table(table_data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ]))
        story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # --- Historical Trends (chart + series data) ---
    story.append(Paragraph(content.historical_trends.heading, h2))
    if content.historical_trends.series:
        chart_bytes = _build_chart(
            content.historical_trends.series,
            title=f"Trends — {content.scope.label}",
        )
        if chart_bytes:
            img_buf = io.BytesIO(chart_bytes)
            story.append(RLImage(img_buf, width=14*cm, height=7*cm))
            story.append(Spacer(1, 0.2*cm))
    story.append(Spacer(1, 0.3*cm))

    # --- Comparative Analysis ---
    story.append(Paragraph(content.comparative_analysis.heading, h2))
    if content.comparative_analysis.rows:
        headers = ["Entity", "Metric", "Period", "Value", "Unit"]
        table_data = [headers] + [
            [str(r.get(k, "")) for k in ("entity", "metric", "period", "value", "unit")]
            for r in content.comparative_analysis.rows
        ]
        t = Table(table_data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # --- Data Quality Warnings ---
    story.append(Paragraph(content.data_quality_warnings.heading, h2))
    if content.data_quality_warnings.open_flags:
        story.append(Paragraph(f"Open Validation Flags ({len(content.data_quality_warnings.open_flags)})", styles["Heading3"]))
        for f in content.data_quality_warnings.open_flags[:20]:
            story.append(Paragraph(
                f"[{f.get('severity','?').upper()}] {f.get('flag_type','')} — "
                f"{f.get('entity_name','')} / {f.get('metric','')} | "
                f"{f.get('detail','')}",
                small,
            ))
    if content.data_quality_warnings.open_conflicts:
        story.append(Paragraph(f"Open Conflicts ({len(content.data_quality_warnings.open_conflicts)})", styles["Heading3"]))
        for c in content.data_quality_warnings.open_conflicts[:20]:
            story.append(Paragraph(
                f"Conflict {c.get('conflict_id','')[:8]}... — "
                f"{c.get('entity_name','')} / {c.get('metric','')} — "
                f"delta {c.get('delta_pct','?')}%",
                small,
            ))
    story.append(Spacer(1, 0.4*cm))

    # --- Recommendations ---
    if content.recommendations:
        _add_narrative(story, content.recommendations.heading, content.recommendations.text, h2, normal)

    # --- Citations ---
    story.append(HRFlowable(width="100%", thickness=0.5))
    story.append(Paragraph("Source Citations", h2))
    for cit in content.citations:
        story.append(Paragraph(
            f"[{cit.claim_key}] {cit.document_filename} "
            f"(p.{cit.page_number or '?'}) — {cit.excerpt[:120]}",
            small,
        ))

    doc.build(story)
    logger.info("PDF exported: %s (%d citations)", output_path, len(content.citations))


def _add_narrative(story, heading, text, h2_style, normal_style):
    story.append(Paragraph(heading, h2_style))
    if text:
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, normal_style))
    else:
        story.append(Paragraph("(Narrative unavailable — see structured data sections.)", normal_style))
    from reportlab.platypus import Spacer
    from reportlab.lib.units import cm
    story.append(Spacer(1, 0.4*cm))
