"""Report export application service (US-019)."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reporting.content_effectiveness_service import (
    ContentEffectivenessReportService,
)
from livelead.application.reporting.funnel_service import FunnelReportService
from livelead.application.reporting.service import DashboardOverviewService
from livelead.application.reporting.source_performance_service import SourcePerformanceReportService
from livelead.domain.reporting.content_effectiveness import InvalidContentGrouping
from livelead.domain.reporting.report_export import (
    ReportExportArtifact,
    ReportExportType,
    UnsupportedReportExport,
    export_content_effectiveness,
    export_dashboard,
    export_funnel,
    export_source_performance,
    normalize_export_format,
    normalize_report_type,
)
from livelead.domain.reporting.source_performance import InvalidSourceGrouping
from livelead.domain.reporting.time_window import InvalidDashboardTimeWindow

logger = logging.getLogger("livelead.report_export")


class ReportExportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def export_report(
        self,
        organization_id: UUID,
        *,
        report_type_raw: str,
        format_raw: str,
        start: date | None = None,
        end: date | None = None,
        preset: str | None = None,
        grouping: str | None = None,
        today: date | None = None,
    ) -> ReportExportArtifact:
        report_type = normalize_report_type(report_type_raw)
        export_format = normalize_export_format(format_raw)

        try:
            if report_type == ReportExportType.DASHBOARD:
                overview = await DashboardOverviewService(self._session).get_overview(
                    organization_id,
                    start=start,
                    end=end,
                    preset=preset,
                    today=today,
                )
                artifact = export_dashboard(overview, export_format)
            elif report_type == ReportExportType.FUNNEL:
                funnel = await FunnelReportService(self._session).get_report(
                    organization_id,
                    start=start,
                    end=end,
                    preset=preset,
                    today=today,
                )
                artifact = export_funnel(funnel, export_format)
            elif report_type == ReportExportType.SOURCE_PERFORMANCE:
                sp = await SourcePerformanceReportService(self._session).get_report(
                    organization_id,
                    grouping=grouping,
                    start=start,
                    end=end,
                    preset=preset,
                    today=today,
                )
                artifact = export_source_performance(sp, export_format)
            elif report_type == ReportExportType.CONTENT_EFFECTIVENESS:
                ce = await ContentEffectivenessReportService(self._session).get_report(
                    organization_id,
                    grouping=grouping,
                    start=start,
                    end=end,
                    preset=preset,
                    today=today,
                )
                artifact = export_content_effectiveness(ce, export_format)
            else:
                raise UnsupportedReportExport(f"unsupported report type: {report_type_raw}")
        except InvalidDashboardTimeWindow:
            raise
        except InvalidSourceGrouping:
            raise
        except InvalidContentGrouping:
            raise

        logger.info(
            "report_export org=%s type=%s format=%s start=%s end=%s preset=%s grouping=%s bytes=%s",
            organization_id,
            artifact.report_type.value,
            artifact.export_format.value,
            start,
            end,
            preset,
            grouping,
            len(artifact.body),
        )
        return artifact
