"""US-019 report export domain rules."""

from datetime import UTC, date, datetime

import pytest

from livelead.domain.reporting.content_effectiveness import (
    CORRELATION_DISCLAIMER,
    ContentEffectivenessFreshness,
    ContentEffectivenessMetrics,
    ContentEffectivenessReport,
    ContentEffectivenessRow,
    ContentEffectivenessWindow,
    ContentGrouping,
)
from livelead.domain.reporting.funnel import (
    FunnelCohort,
    FunnelFreshness,
    FunnelReport,
    FunnelStep,
)
from livelead.domain.reporting.models import (
    DashboardMetricCard,
    DashboardOverview,
    DashboardTimeWindow,
    MetricAvailability,
    WidgetFreshness,
)
from livelead.domain.reporting.report_export import (
    ReportExportFormat,
    UnsupportedReportExport,
    export_dashboard,
    export_funnel,
    normalize_export_format,
    normalize_report_type,
)
from livelead.domain.reporting.source_performance import (
    SourceGrouping,
    SourcePerformanceFreshness,
    SourcePerformanceMetrics,
    SourcePerformanceReport,
    SourcePerformanceRow,
    SourcePerformanceWindow,
)


def _ts() -> datetime:
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_normalize_report_type_and_format():
    assert normalize_report_type("funnel").value == "funnel"
    assert normalize_export_format("csv") == ReportExportFormat.CSV
    assert normalize_export_format("pdf") == ReportExportFormat.PRINTABLE
    assert normalize_export_format("html") == ReportExportFormat.PRINTABLE


def test_unsupported_type_and_format():
    with pytest.raises(UnsupportedReportExport, match="unsupported report type"):
        normalize_report_type("revenue")
    with pytest.raises(UnsupportedReportExport, match="unsupported export format"):
        normalize_export_format("xlsx")


def test_export_dashboard_csv_includes_window_and_widgets():
    overview = DashboardOverview(
        time_window=DashboardTimeWindow(
            start=date(2026, 5, 1), end=date(2026, 5, 31), preset="last_30_days"
        ),
        widgets=(
            DashboardMetricCard(
                key="events_discovered",
                label="Events discovered",
                availability=MetricAvailability.EMPTY,
                value=0,
                freshness=WidgetFreshness(last_updated_at=None, source="events.observed_at"),
            ),
        ),
        generated_at=_ts(),
    )
    artifact = export_dashboard(overview, ReportExportFormat.CSV)
    text = artifact.body.decode("utf-8")
    assert "window_start" in text
    assert "events_discovered" in text
    assert artifact.filename.endswith(".csv")


def test_export_funnel_printable_has_steps():
    report = FunnelReport(
        cohort=FunnelCohort(start=date(2026, 5, 1), end=date(2026, 5, 7), preset="last_7_days"),
        steps=(FunnelStep("event", "Events discovered", 3, None),),
        unattributed=None,
        freshness=FunnelFreshness(last_updated_at=_ts(), source="events.observed_at"),
        generated_at=_ts(),
    )
    artifact = export_funnel(report, ReportExportFormat.PRINTABLE)
    html = artifact.body.decode("utf-8")
    assert "Events discovered" in html
    assert "last_7_days" in html or "2026-05-01" in html
    assert artifact.media_type.startswith("text/html")


def test_export_source_performance_csv_headers():
    report = SourcePerformanceReport(
        grouping=SourceGrouping.CAMPAIGN,
        grouping_label="Campaign",
        window=SourcePerformanceWindow(
            start=date(2026, 5, 1), end=date(2026, 5, 7), preset="last_7_days"
        ),
        rows=(
            SourcePerformanceRow(
                "c1",
                "Camp",
                SourcePerformanceMetrics(events_discovered=2, leads_created=1),
            ),
        ),
        unattributed=None,
        freshness=SourcePerformanceFreshness(last_updated_at=_ts(), source="events"),
        generated_at=_ts(),
    )
    from livelead.domain.reporting.report_export import export_source_performance

    artifact = export_source_performance(report, ReportExportFormat.CSV)
    assert b"events_discovered" in artifact.body
    assert b"Camp" in artifact.body


def test_export_content_effectiveness_carries_correlation_note():
    report = ContentEffectivenessReport(
        grouping=ContentGrouping.CONTENT_TYPE,
        grouping_label="Content type",
        window=ContentEffectivenessWindow(
            start=date(2026, 5, 1), end=date(2026, 5, 7), preset=None
        ),
        rows=(
            ContentEffectivenessRow(
                "email",
                "Email",
                ContentEffectivenessMetrics(content_used=1, outcomes_linked=1),
            ),
        ),
        unattributed=None,
        freshness=ContentEffectivenessFreshness(last_updated_at=None, source="content"),
        correlation_note=CORRELATION_DISCLAIMER,
        generated_at=_ts(),
    )
    from livelead.domain.reporting.report_export import export_content_effectiveness

    artifact = export_content_effectiveness(report, ReportExportFormat.CSV)
    assert CORRELATION_DISCLAIMER.encode() in artifact.body
