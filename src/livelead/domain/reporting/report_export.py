"""Report export mapping and validation (US-019)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from livelead.domain.reporting.content_effectiveness import ContentEffectivenessReport
from livelead.domain.reporting.funnel import FunnelReport
from livelead.domain.reporting.models import DashboardOverview
from livelead.domain.reporting.source_performance import SourcePerformanceReport


class ReportExportType(StrEnum):
    DASHBOARD = "dashboard"
    FUNNEL = "funnel"
    SOURCE_PERFORMANCE = "source_performance"
    CONTENT_EFFECTIVENESS = "content_effectiveness"


class ReportExportFormat(StrEnum):
    CSV = "csv"
    PRINTABLE = "printable"


REPORT_TYPE_LABELS: dict[ReportExportType, str] = {
    ReportExportType.DASHBOARD: "Dashboard overview",
    ReportExportType.FUNNEL: "Conversion funnel",
    ReportExportType.SOURCE_PERFORMANCE: "Source performance",
    ReportExportType.CONTENT_EFFECTIVENESS: "Content effectiveness",
}


class UnsupportedReportExport(ValueError):
    """Unsupported report type or export format combination."""


def normalize_report_type(raw: str | None) -> ReportExportType:
    if not raw or not raw.strip():
        raise UnsupportedReportExport("report type is required")
    key = raw.strip().lower()
    try:
        return ReportExportType(key)
    except ValueError as exc:
        raise UnsupportedReportExport(f"unsupported report type: {raw}") from exc


def normalize_export_format(raw: str | None) -> ReportExportFormat:
    if not raw or not raw.strip():
        raise UnsupportedReportExport("export format is required")
    key = raw.strip().lower()
    if key in ("pdf", "html", "printable"):
        return ReportExportFormat.PRINTABLE
    try:
        return ReportExportFormat(key)
    except ValueError as exc:
        raise UnsupportedReportExport(f"unsupported export format: {raw}") from exc


@dataclass(frozen=True, slots=True)
class ReportExportArtifact:
    report_type: ReportExportType
    export_format: ReportExportFormat
    filename: str
    media_type: str
    body: bytes
    generated_at: datetime


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _window_line(start, end, preset: str | None) -> str:
    line = f"{start} → {end}"
    if preset:
        line += f" (preset: {preset})"
    return line


def _csv_rows(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _printable_document(title: str, meta_lines: list[str], body_html: str) -> bytes:
    meta = "".join(f"<p class='meta'>{_escape_html(line)}</p>" for line in meta_lines)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{_escape_html(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #0f172a; }}
h1 {{ font-size: 1.25rem; margin-bottom: 0.5rem; }}
.meta {{ font-size: 0.75rem; color: #64748b; margin: 0.15rem 0; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: 0.85rem; }}
th, td {{ border: 1px solid #e2e8f0; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #f8fafc; }}
.note {{ font-size: 0.75rem; color: #475569; margin-top: 1rem; max-width: 48rem; }}
@media print {{ body {{ margin: 1rem; }} }}
</style>
</head>
<body>
<h1>{_escape_html(title)}</h1>
{meta}
{body_html}
</body>
</html>"""
    return html.encode("utf-8")


def export_dashboard(
    overview: DashboardOverview,
    fmt: ReportExportFormat,
) -> ReportExportArtifact:
    label = REPORT_TYPE_LABELS[ReportExportType.DASHBOARD]
    tw = overview.time_window
    meta = [
        f"Time window: {_window_line(tw.start, tw.end, tw.preset)}",
        f"Generated at: {_iso(overview.generated_at)}",
    ]
    if fmt == ReportExportFormat.CSV:
        rows: list[list[str]] = [
            ["report", label],
            ["window_start", str(tw.start)],
            ["window_end", str(tw.end)],
            ["preset", tw.preset or ""],
            ["generated_at", _iso(overview.generated_at)],
            [],
            [
                "widget_key",
                "widget_label",
                "availability",
                "value",
                "freshness_at",
                "freshness_source",
            ],
        ]
        for w in overview.widgets:
            rows.append(
                [
                    w.key,
                    w.label,
                    w.availability.value,
                    "" if w.value is None else str(w.value),
                    _iso(w.freshness.last_updated_at),
                    w.freshness.source,
                ]
            )
        body = _csv_rows(rows)
        return ReportExportArtifact(
            report_type=ReportExportType.DASHBOARD,
            export_format=fmt,
            filename="dashboard-overview.csv",
            media_type="text/csv; charset=utf-8",
            body=body,
            generated_at=overview.generated_at,
        )
    table_rows = "".join(
        f"<tr><td>{_escape_html(w.label)}</td>"
        f"<td>{_escape_html(w.availability.value)}</td>"
        f"<td>{'' if w.value is None else w.value}</td>"
        f"<td>{_escape_html(_iso(w.freshness.last_updated_at))}</td></tr>"
        for w in overview.widgets
    )
    body_html = (
        "<table><thead><tr><th>Metric</th><th>Status</th><th>Value</th>"
        "<th>Freshness</th></tr></thead><tbody>"
        f"{table_rows}</tbody></table>"
    )
    return ReportExportArtifact(
        report_type=ReportExportType.DASHBOARD,
        export_format=fmt,
        filename="dashboard-overview.html",
        media_type="text/html; charset=utf-8",
        body=_printable_document(label, meta, body_html),
        generated_at=overview.generated_at,
    )


def export_funnel(report: FunnelReport, fmt: ReportExportFormat) -> ReportExportArtifact:
    label = REPORT_TYPE_LABELS[ReportExportType.FUNNEL]
    c = report.cohort
    meta = [
        f"Cohort: {_window_line(c.start, c.end, c.preset)}",
        f"Freshness: {_iso(report.freshness.last_updated_at)} ({report.freshness.source})",
        f"Generated at: {_iso(report.generated_at)}",
    ]
    if fmt == ReportExportFormat.CSV:
        rows: list[list[str]] = [
            ["report", label],
            ["cohort_start", str(c.start)],
            ["cohort_end", str(c.end)],
            ["preset", c.preset or ""],
            ["freshness_at", _iso(report.freshness.last_updated_at)],
            ["generated_at", _iso(report.generated_at)],
            [],
            ["step_key", "step_label", "count", "note"],
        ]
        for s in report.steps:
            rows.append([s.key, s.label, str(s.count), s.note or ""])
        if report.unattributed:
            rows.append([])
            rows.append(
                ["unattributed_manual_leads", str(report.unattributed.manual_leads_in_cohort)]
            )
            rows.append(["unattributed_note", report.unattributed.explanation])
        body = _csv_rows(rows)
        return ReportExportArtifact(
            report_type=ReportExportType.FUNNEL,
            export_format=fmt,
            filename="funnel-report.csv",
            media_type="text/csv; charset=utf-8",
            body=body,
            generated_at=report.generated_at,
        )
    step_rows = "".join(
        f"<tr><td>{_escape_html(s.label)}</td><td>{s.count}</td>"
        f"<td>{_escape_html(s.note or '')}</td></tr>"
        for s in report.steps
    )
    notes = f"<p class='note'>{_escape_html(c.rule)}</p>"
    if report.unattributed:
        notes += (
            f"<p class='note'>{_escape_html(report.unattributed.explanation)} "
            f"({report.unattributed.manual_leads_in_cohort} manual in cohort)</p>"
        )
    body_html = (
        "<table><thead><tr><th>Step</th><th>Count</th><th>Note</th></tr></thead><tbody>"
        f"{step_rows}</tbody></table>{notes}"
    )
    return ReportExportArtifact(
        report_type=ReportExportType.FUNNEL,
        export_format=fmt,
        filename="funnel-report.html",
        media_type="text/html; charset=utf-8",
        body=_printable_document(label, meta, body_html),
        generated_at=report.generated_at,
    )


def export_source_performance(
    report: SourcePerformanceReport,
    fmt: ReportExportFormat,
) -> ReportExportArtifact:
    label = REPORT_TYPE_LABELS[ReportExportType.SOURCE_PERFORMANCE]
    w = report.window
    meta = [
        f"Grouping: {report.grouping_label}",
        f"Time window: {_window_line(w.start, w.end, w.preset)}",
        f"Freshness: {_iso(report.freshness.last_updated_at)} ({report.freshness.source})",
        f"Generated at: {_iso(report.generated_at)}",
    ]
    if fmt == ReportExportFormat.CSV:
        rows: list[list[str]] = [
            ["report", label],
            ["grouping", report.grouping.value],
            ["window_start", str(w.start)],
            ["window_end", str(w.end)],
            ["preset", w.preset or ""],
            ["generated_at", _iso(report.generated_at)],
            [],
            [
                "group_key",
                "group_label",
                "events_discovered",
                "events_prioritized",
                "leads_created",
                "opportunities",
            ],
        ]
        for r in report.rows:
            m = r.metrics
            rows.append(
                [
                    r.group_key,
                    r.group_label,
                    str(m.events_discovered),
                    str(m.events_prioritized),
                    str(m.leads_created),
                    str(m.opportunities),
                ]
            )
        if report.unattributed:
            rows.append([])
            rows.append(
                [
                    "unattributed_events",
                    str(report.unattributed.events_without_source_link),
                ]
            )
            rows.append(["unattributed_leads", str(report.unattributed.leads_without_group_key)])
        body = _csv_rows(rows)
        return ReportExportArtifact(
            report_type=ReportExportType.SOURCE_PERFORMANCE,
            export_format=fmt,
            filename="source-performance.csv",
            media_type="text/csv; charset=utf-8",
            body=body,
            generated_at=report.generated_at,
        )
    data_rows = "".join(
        f"<tr><td>{_escape_html(r.group_label)}</td>"
        f"<td>{r.metrics.events_discovered}</td>"
        f"<td>{r.metrics.events_prioritized}</td>"
        f"<td>{r.metrics.leads_created}</td>"
        f"<td>{r.metrics.opportunities}</td></tr>"
        for r in report.rows
    )
    body_html = (
        "<table><thead><tr><th>Group</th><th>Discovered</th><th>Prioritized</th>"
        "<th>Leads</th><th>Opportunities</th></tr></thead><tbody>"
        f"{data_rows}</tbody></table>"
    )
    if report.unattributed:
        body_html += f"<p class='note'>{_escape_html(report.unattributed.explanation)}</p>"
    return ReportExportArtifact(
        report_type=ReportExportType.SOURCE_PERFORMANCE,
        export_format=fmt,
        filename="source-performance.html",
        media_type="text/html; charset=utf-8",
        body=_printable_document(label, meta, body_html),
        generated_at=report.generated_at,
    )


def export_content_effectiveness(
    report: ContentEffectivenessReport,
    fmt: ReportExportFormat,
) -> ReportExportArtifact:
    label = REPORT_TYPE_LABELS[ReportExportType.CONTENT_EFFECTIVENESS]
    w = report.window
    meta = [
        f"Grouping: {report.grouping_label}",
        f"Time window: {_window_line(w.start, w.end, w.preset)}",
        f"Freshness: {_iso(report.freshness.last_updated_at)} ({report.freshness.source})",
        f"Generated at: {_iso(report.generated_at)}",
    ]
    if fmt == ReportExportFormat.CSV:
        rows: list[list[str]] = [
            ["report", label],
            ["grouping", report.grouping.value],
            ["window_start", str(w.start)],
            ["window_end", str(w.end)],
            ["preset", w.preset or ""],
            ["correlation_note", report.correlation_note],
            ["generated_at", _iso(report.generated_at)],
            [],
            [
                "group_key",
                "group_label",
                "content_used",
                "outcomes_linked",
                "outcomes_contact",
                "outcomes_response",
                "outcomes_meeting",
                "outcomes_opportunity",
            ],
        ]
        for r in report.rows:
            m = r.metrics
            rows.append(
                [
                    r.group_key,
                    r.group_label,
                    str(m.content_used),
                    str(m.outcomes_linked),
                    str(m.outcomes_contact),
                    str(m.outcomes_response),
                    str(m.outcomes_meeting),
                    str(m.outcomes_opportunity),
                ]
            )
        body = _csv_rows(rows)
        return ReportExportArtifact(
            report_type=ReportExportType.CONTENT_EFFECTIVENESS,
            export_format=fmt,
            filename="content-effectiveness.csv",
            media_type="text/csv; charset=utf-8",
            body=body,
            generated_at=report.generated_at,
        )
    data_rows = "".join(
        f"<tr><td>{_escape_html(r.group_label)}</td>"
        f"<td>{r.metrics.content_used}</td>"
        f"<td>{r.metrics.outcomes_linked}</td>"
        f"<td>{r.metrics.outcomes_opportunity}</td></tr>"
        for r in report.rows
    )
    body_html = (
        f"<p class='note'>{_escape_html(report.correlation_note)}</p>"
        "<table><thead><tr><th>Group</th><th>Content used</th><th>Outcomes linked</th>"
        "<th>Opportunities</th></tr></thead><tbody>"
        f"{data_rows}</tbody></table>"
    )
    if report.unattributed:
        body_html += f"<p class='note'>{_escape_html(report.unattributed.explanation)}</p>"
    return ReportExportArtifact(
        report_type=ReportExportType.CONTENT_EFFECTIVENESS,
        export_format=fmt,
        filename="content-effectiveness.html",
        media_type="text/html; charset=utf-8",
        body=_printable_document(label, meta, body_html),
        generated_at=report.generated_at,
    )
