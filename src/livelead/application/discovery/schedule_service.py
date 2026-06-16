"""Discovery schedule application service (US-035)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.discovery.criteria_snapshot import build_criteria_snapshot
from livelead.domain.discovery.schedule_recurrence import (
    compute_next_run,
    parse_recurrence,
    recurrence_to_json,
)
from livelead.domain.discovery.schedule_state import ScheduleEnabledState, schedule_may_dispatch
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.db.models import CampaignRow, DiscoveryJobRow, DiscoveryScheduleRow
from livelead.infrastructure.db.repositories.discovery_jobs import DiscoveryJobRepository
from livelead.infrastructure.db.repositories.discovery_schedules import DiscoveryScheduleRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source

logger = logging.getLogger("livelead.discovery_schedule")


class ScheduleValidationError(ValueError):
    pass


async def _resolve_source_ids(
    session: AsyncSession,
    *,
    campaign_id: UUID,
    organization_id: UUID,
    requested: list[UUID] | None,
) -> list[str]:
    src_repo = SourceRepository(session)
    if requested:
        for sid in requested:
            row = await src_repo.get(sid, organization_id)
            if not row:
                raise ScheduleValidationError(f"source missing: {sid}")
            d = evaluate_source_policy(row_to_source(row))
            if not d.runnable:
                raise ScheduleValidationError(f"source not runnable: {sid}")
        return [str(s) for s in requested]

    pinned = await src_repo.list_campaign_source_ids(campaign_id, organization_id)
    runnable_pinned: list[str] = []
    for sid in pinned:
        row = await src_repo.get(sid, organization_id)
        if not row:
            continue
        if evaluate_source_policy(row_to_source(row)).runnable:
            runnable_pinned.append(str(sid))
    if runnable_pinned:
        return runnable_pinned

    all_src = await src_repo.list_for_organization(organization_id)
    runnable = [s for s in all_src if evaluate_source_policy(s).runnable]
    if not runnable:
        raise ScheduleValidationError("no runnable sources")
    return [str(runnable[0].id)]


class DiscoveryScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._schedules = DiscoveryScheduleRepository(session)
        self._jobs = DiscoveryJobRepository(session)

    async def create(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        recurrence: dict,
        source_ids: list[UUID] | None,
        actor: str,
    ) -> DiscoveryScheduleRow:
        camp = await self._session.execute(
            select(CampaignRow).where(
                CampaignRow.id == str(campaign_id),
                CampaignRow.organization_id == str(organization_id),
            )
        )
        camp_row = camp.scalar_one_or_none()
        if not camp_row:
            raise ScheduleValidationError("campaign not found")

        try:
            spec = parse_recurrence(recurrence)
        except ValueError as exc:
            raise ScheduleValidationError(str(exc)) from exc

        resolved = await _resolve_source_ids(
            self._session,
            campaign_id=campaign_id,
            organization_id=organization_id,
            requested=source_ids,
        )
        template = {
            "campaign_id": str(campaign_id),
            "source_ids": resolved,
            "recurrence_summary": spec.summary(),
        }
        row = await self._schedules.create(
            organization_id=organization_id,
            campaign_id=campaign_id,
            recurrence=recurrence,
            source_ids=resolved,
            template=template,
            created_by=actor,
        )
        return row

    async def list_for_campaign(
        self, campaign_id: UUID, organization_id: UUID
    ) -> list[DiscoveryScheduleRow]:
        return await self._schedules.list_for_campaign(campaign_id, organization_id)

    async def get(self, schedule_id: UUID, organization_id: UUID) -> DiscoveryScheduleRow | None:
        return await self._schedules.get(schedule_id, organization_id)

    async def patch(
        self,
        row: DiscoveryScheduleRow,
        *,
        recurrence: dict | None = None,
        enabled_state: str | None = None,
        source_ids: list[UUID] | None = None,
        organization_id: UUID,
    ) -> DiscoveryScheduleRow:
        if recurrence is not None:
            await self._schedules.update_recurrence(row, recurrence)
        if source_ids is not None:
            resolved = await _resolve_source_ids(
                self._session,
                campaign_id=UUID(row.campaign_id),
                organization_id=organization_id,
                requested=source_ids,
            )
            await self._schedules.set_source_ids(row, resolved)
        if enabled_state is not None:
            try:
                state = ScheduleEnabledState(enabled_state)
            except ValueError as exc:
                raise ScheduleValidationError("invalid enabled_state") from exc
            await self._schedules.set_enabled_state(row, state)
            if state == ScheduleEnabledState.ENABLED:
                spec = parse_recurrence(json.loads(row.recurrence_json))
                row.next_run_at = compute_next_run(spec, after=datetime.now(UTC))
        return row

    async def latest_job_summary(
        self, row: DiscoveryScheduleRow, organization_id: UUID
    ) -> dict | None:
        if not row.last_dispatched_job_id:
            return None
        job = await self._jobs.get(UUID(row.last_dispatched_job_id), organization_id)
        if not job:
            return None
        return {"job_id": job.id, "status": job.status, "error_summary": job.error_summary}