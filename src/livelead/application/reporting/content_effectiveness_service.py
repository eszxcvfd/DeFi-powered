"""Content-effectiveness application service (US-018)."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.content_effectiveness import (
    CORRELATION_DISCLAIMER,
    GROUPING_LABELS,
    ContentEffectivenessFreshness,
    ContentEffectivenessReport,
    ContentEffectivenessWindow,
    InvalidContentGrouping,
    UnattributedContentSummary,
    build_unattributed_explanation,
    normalize_content_grouping,
)
from livelead.domain.reporting.time_window import (
    InvalidDashboardTimeWindow,
    normalize_time_window,
    window_bounds_utc,
)
from livelead.infrastructure.db.repositories.content_effectiveness_report import (
    ContentEffectivenessReportRepository,
)

logger = logging.getLogger("livelead.content_effectiveness")


class ContentEffectivenessReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ContentEffectivenessReportRepository(session)

    async def get_report(
        self,
        organization_id: UUID,
        *,
        grouping: str | None = None,
        start: date | None = None,
        end: date | None = None,
        preset: str | None = None,
        today: date | None = None,
    ) -> ContentEffectivenessReport:
        try:
            window = normalize_time_window(start=start, end=end, preset=preset, today=today)
        except InvalidDashboardTimeWindow:
            raise
        try:
            group = normalize_content_grouping(grouping)
        except InvalidContentGrouping:
            raise

        start_dt, end_ex = window_bounds_utc(window)
        rows, unattributed_raw, last = await self._repo.build_report_rows(
            organization_id, group, start_dt, end_ex
        )

        unattributed = None
        if unattributed_raw is not None and (
            unattributed_raw.used_content_without_metadata > 0
            or unattributed_raw.outcomes_without_content_link > 0
        ):
            unattributed = UnattributedContentSummary(
                used_content_without_metadata=unattributed_raw.used_content_without_metadata,
                outcomes_without_content_link=unattributed_raw.outcomes_without_content_link,
                explanation=build_unattributed_explanation(group),
            )

        report = ContentEffectivenessReport(
            grouping=group,
            grouping_label=GROUPING_LABELS[group],
            window=ContentEffectivenessWindow(
                start=window.start, end=window.end, preset=window.preset
            ),
            rows=rows,
            unattributed=unattributed,
            freshness=ContentEffectivenessFreshness(
                last_updated_at=last,
                source="content_drafts.usage_status.lead_activities",
            ),
            correlation_note=CORRELATION_DISCLAIMER,
            generated_at=datetime.now(UTC),
        )
        logger.info(
            "content_effectiveness_report org=%s grouping=%s start=%s end=%s rows=%s unattributed_meta=%s unattributed_outcomes=%s",
            organization_id,
            group.value,
            window.start.isoformat(),
            window.end.isoformat(),
            len(rows),
            unattributed.used_content_without_metadata if unattributed else 0,
            unattributed.outcomes_without_content_link if unattributed else 0,
        )
        return report
