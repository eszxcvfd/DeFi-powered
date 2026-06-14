"""Source-performance application service (US-017)."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.source_performance import (
    GROUPING_LABELS,
    InvalidSourceGrouping,
    SourcePerformanceFreshness,
    SourcePerformanceReport,
    SourcePerformanceWindow,
    UnattributedSourceSummary,
    build_unattributed_explanation,
    normalize_grouping,
)
from livelead.domain.reporting.time_window import (
    InvalidDashboardTimeWindow,
    normalize_time_window,
    window_bounds_utc,
)
from livelead.infrastructure.db.repositories.source_performance_report import (
    SourcePerformanceReportRepository,
)

logger = logging.getLogger("livelead.source_performance")


class SourcePerformanceReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SourcePerformanceReportRepository(session)

    async def get_report(
        self,
        organization_id: UUID,
        *,
        grouping: str | None = None,
        start: date | None = None,
        end: date | None = None,
        preset: str | None = None,
        today: date | None = None,
    ) -> SourcePerformanceReport:
        try:
            window = normalize_time_window(start=start, end=end, preset=preset, today=today)
        except InvalidDashboardTimeWindow:
            raise
        try:
            group = normalize_grouping(grouping)
        except InvalidSourceGrouping:
            raise

        start_dt, end_ex = window_bounds_utc(window)
        rows, unattributed_raw, last = await self._repo.build_report_rows(
            organization_id, group, start_dt, end_ex
        )

        unattributed = None
        if unattributed_raw is not None and (
            unattributed_raw.events_without_source_link > 0
            or unattributed_raw.leads_without_group_key > 0
        ):
            unattributed = UnattributedSourceSummary(
                events_without_source_link=unattributed_raw.events_without_source_link,
                leads_without_group_key=unattributed_raw.leads_without_group_key,
                explanation=build_unattributed_explanation(group),
            )

        report = SourcePerformanceReport(
            grouping=group,
            grouping_label=GROUPING_LABELS[group],
            window=SourcePerformanceWindow(
                start=window.start, end=window.end, preset=window.preset
            ),
            rows=rows,
            unattributed=unattributed,
            freshness=SourcePerformanceFreshness(
                last_updated_at=last,
                source="events.leads.event_scores.lead_outcomes",
            ),
            generated_at=datetime.now(UTC),
        )
        logger.info(
            "source_performance_report org=%s grouping=%s start=%s end=%s rows=%s unattributed_events=%s unattributed_leads=%s",
            organization_id,
            group.value,
            window.start.isoformat(),
            window.end.isoformat(),
            len(rows),
            unattributed.events_without_source_link if unattributed else 0,
            unattributed.leads_without_group_key if unattributed else 0,
        )
        return report
