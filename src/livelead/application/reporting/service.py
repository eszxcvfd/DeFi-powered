"""Dashboard overview application service (US-014)."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.metrics import classify_count_metric
from livelead.domain.reporting.models import DashboardOverview, DashboardTimeWindow
from livelead.domain.reporting.time_window import (
    InvalidDashboardTimeWindow,
    normalize_time_window,
    window_bounds_utc,
)
from livelead.infrastructure.db.repositories.dashboard_overview import DashboardOverviewRepository

logger = logging.getLogger("livelead.dashboard")


class DashboardOverviewService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DashboardOverviewRepository(session)

    async def get_overview(
        self,
        organization_id: UUID,
        *,
        start: date | None = None,
        end: date | None = None,
        preset: str | None = None,
        today: date | None = None,
    ) -> DashboardOverview:
        try:
            window = normalize_time_window(start=start, end=end, preset=preset, today=today)
        except InvalidDashboardTimeWindow:
            raise

        start_dt, end_ex = window_bounds_utc(window)
        has_events = await self._repo.org_has_any_events(organization_id)
        has_scores = await self._repo.org_has_any_scores(organization_id)
        has_leads = await self._repo.org_has_any_leads(organization_id)
        has_content = await self._repo.org_has_any_content(organization_id)

        widgets = []

        c, ts = await self._repo.count_events_discovered(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="events_discovered",
                label="Events discovered",
                count=c,
                max_observed_at=ts,
                freshness_source="events.observed_at",
                durable_source_exists=has_events,
                unavailable_reason="No events have been discovered yet.",
            )
        )

        c, ts = await self._repo.count_prioritized_events(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="events_prioritized",
                label="Events prioritized",
                count=c,
                max_observed_at=ts,
                freshness_source="event_scores.calculated_at",
                durable_source_exists=has_scores,
                unavailable_reason="No event scores recorded yet.",
            )
        )

        c, ts = await self._repo.count_events_watched_or_engaged(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="events_watched_or_engaged",
                label="Events watched or engaged",
                count=c,
                max_observed_at=ts,
                freshness_source="leads.stage",
                durable_source_exists=has_leads,
                unavailable_reason="No leads linked to events yet.",
            )
        )

        c, ts = await self._repo.count_new_leads(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="leads_new",
                label="New leads",
                count=c,
                max_observed_at=ts,
                freshness_source="leads.created_at",
                durable_source_exists=has_leads,
                unavailable_reason="No leads in the pipeline yet.",
            )
        )

        c, ts = await self._repo.count_content_created(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="content_created",
                label="Content created",
                count=c,
                max_observed_at=ts,
                freshness_source="content.generated_at",
                durable_source_exists=has_content,
                unavailable_reason="No generated content yet.",
            )
        )

        c, ts = await self._repo.count_content_approved(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="content_approved",
                label="Content approved",
                count=c,
                max_observed_at=ts,
                freshness_source="content.lifecycle",
                durable_source_exists=has_content,
                unavailable_reason="No content drafts yet.",
            )
        )

        c, ts = await self._repo.count_content_used(organization_id, start_dt, end_ex)
        widgets.append(
            classify_count_metric(
                key="content_used",
                label="Content used",
                count=c,
                max_observed_at=ts,
                freshness_source="content.usage_status",
                durable_source_exists=has_content,
                unavailable_reason="No content usage recorded yet.",
            )
        )

        for key, label, source, outcome_type in (
            ("responses", "Responses", "lead_outcomes.response", "response"),
            ("meetings_scheduled", "Meetings scheduled", "lead_outcomes.meeting", "meeting"),
            ("opportunities", "Opportunities", "lead_outcomes.opportunity", "opportunity"),
        ):
            has_outcomes = await self._repo.org_has_outcome_activity(organization_id, outcome_type)
            has_leads_for_empty = await self._repo.org_has_any_leads(organization_id)
            c, ts = await self._repo.count_outcome_entries(
                organization_id, outcome_type, start_dt, end_ex
            )
            widgets.append(
                classify_count_metric(
                    key=key,
                    label=label,
                    count=c,
                    max_observed_at=ts,
                    freshness_source=source,
                    durable_source_exists=has_outcomes or has_leads_for_empty,
                    unavailable_reason=f"No recorded '{outcome_type}' outcomes yet.",
                )
            )

        overview = DashboardOverview(
            time_window=DashboardTimeWindow(
                start=window.start, end=window.end, preset=window.preset
            ),
            widgets=tuple(widgets),
            generated_at=datetime.now(UTC),
        )
        logger.info(
            "dashboard_overview org=%s start=%s end=%s preset=%s widgets=%s",
            organization_id,
            window.start.isoformat(),
            window.end.isoformat(),
            window.preset,
            ",".join(f"{w.key}:{w.availability.value}" for w in widgets),
        )
        return overview
