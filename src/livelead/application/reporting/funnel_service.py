"""Funnel report application service (US-016)."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.funnel import (
    FUNNEL_COHORT_RULE,
    FunnelCohort,
    FunnelFreshness,
    FunnelReport,
    UnattributedLeadSummary,
    build_funnel_steps,
)
from livelead.domain.reporting.time_window import (
    InvalidDashboardTimeWindow,
    normalize_time_window,
    window_bounds_utc,
)
from livelead.infrastructure.db.repositories.funnel_report import FunnelReportRepository

logger = logging.getLogger("livelead.funnel")


class FunnelReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = FunnelReportRepository(session)

    async def get_report(
        self,
        organization_id: UUID,
        *,
        start: date | None = None,
        end: date | None = None,
        preset: str | None = None,
        today: date | None = None,
    ) -> FunnelReport:
        try:
            window = normalize_time_window(start=start, end=end, preset=preset, today=today)
        except InvalidDashboardTimeWindow:
            raise

        start_dt, end_ex = window_bounds_utc(window)
        events, ts_ev = await self._repo.count_events_in_window(organization_id, start_dt, end_ex)
        leads, ts_lead = await self._repo.count_leads_in_window(organization_id, start_dt, end_ex)
        manual = await self._repo.count_manual_leads_in_window(organization_id, start_dt, end_ex)

        outcome_counts: dict[str, tuple[int, datetime | None]] = {}
        for key in ("contact", "response", "meeting", "opportunity"):
            outcome_counts[key] = await self._repo.count_distinct_leads_with_outcome(
                organization_id, key, start_dt, end_ex
            )

        freshness_candidates = [
            ts for ts in [ts_ev, ts_lead, *[v[1] for v in outcome_counts.values()]] if ts
        ]
        last = max(freshness_candidates) if freshness_candidates else None

        unattributed = None
        if manual > 0:
            unattributed = UnattributedLeadSummary(
                manual_leads_in_cohort=manual,
                explanation=(
                    "Manual leads without an event link are excluded from the event step "
                    "but included in the lead step and downstream outcome steps when applicable."
                ),
            )

        steps = build_funnel_steps(
            events=events,
            leads=leads,
            contact=outcome_counts["contact"][0],
            response=outcome_counts["response"][0],
            meeting=outcome_counts["meeting"][0],
            opportunity=outcome_counts["opportunity"][0],
            manual_leads=manual,
        )

        report = FunnelReport(
            cohort=FunnelCohort(
                start=window.start,
                end=window.end,
                preset=window.preset,
                rule=FUNNEL_COHORT_RULE,
            ),
            steps=steps,
            unattributed=unattributed,
            freshness=FunnelFreshness(last_updated_at=last, source="events.leads.lead_outcomes"),
            generated_at=datetime.now(UTC),
        )
        logger.info(
            "funnel_report org=%s start=%s end=%s events=%s leads=%s manual=%s contact=%s response=%s meeting=%s opportunity=%s",
            organization_id,
            window.start.isoformat(),
            window.end.isoformat(),
            events,
            leads,
            manual,
            outcome_counts["contact"][0],
            outcome_counts["response"][0],
            outcome_counts["meeting"][0],
            outcome_counts["opportunity"][0],
        )
        return report
