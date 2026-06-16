"""AI feedback persistence (US-038)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.ai_feedback.models import (
    AiFeedbackAggregate,
    AiFeedbackProjection,
    AiFeedbackTargetType,
)
from livelead.infrastructure.db.models import (
    AiFeedbackEventRow,
    AudienceHypothesisRow,
    DiscoveryCopilotResponseRow,
    EventRow,
)


class AiFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        organization_id: UUID,
        target_type: AiFeedbackTargetType,
        target_id: UUID,
        actor_key: str,
        state: str,
        reason_code: str | None,
        note: str | None,
        prior_state: str | None,
    ) -> AiFeedbackEventRow:
        row = AiFeedbackEventRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            target_type=target_type.value,
            target_id=str(target_id),
            actor_key=actor_key,
            state=state,
            reason_code=reason_code,
            note=note,
            prior_state=prior_state,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_viewer_projection(
        self,
        organization_id: UUID,
        actor_key: str,
        target_type: AiFeedbackTargetType,
        target_id: UUID,
    ) -> AiFeedbackProjection | None:
        result = await self._session.execute(
            select(AiFeedbackEventRow)
            .where(
                AiFeedbackEventRow.organization_id == str(organization_id),
                AiFeedbackEventRow.actor_key == actor_key,
                AiFeedbackEventRow.target_type == target_type.value,
                AiFeedbackEventRow.target_id == str(target_id),
            )
            .order_by(AiFeedbackEventRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AiFeedbackProjection(
            target_type=target_type,
            target_id=target_id,
            state=row.state,
            reason_code=row.reason_code,
            note=row.note,
            actor_key=row.actor_key,
            updated_at=row.created_at,
        )

    async def project_for_viewer(
        self,
        organization_id: UUID,
        actor_key: str,
        target_type: AiFeedbackTargetType,
        target_ids: list[UUID],
    ) -> dict[UUID, AiFeedbackProjection]:
        if not target_ids:
            return {}
        out: dict[UUID, AiFeedbackProjection] = {}
        for tid in target_ids:
            proj = await self.get_viewer_projection(organization_id, actor_key, target_type, tid)
            if proj is not None:
                out[tid] = proj
        return out

    async def aggregate_for_target(
        self,
        organization_id: UUID,
        target_type: AiFeedbackTargetType,
        target_id: UUID,
    ) -> AiFeedbackAggregate:
        result = await self._session.execute(
            select(AiFeedbackEventRow.state, func.count())
            .where(
                AiFeedbackEventRow.organization_id == str(organization_id),
                AiFeedbackEventRow.target_type == target_type.value,
                AiFeedbackEventRow.target_id == str(target_id),
            )
            .group_by(AiFeedbackEventRow.state)
        )
        counts = {row[0]: int(row[1]) for row in result.all()}
        if target_type == AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE:
            return AiFeedbackAggregate(
                helpful_count=counts.get("helpful", 0),
                not_helpful_count=counts.get("not_helpful", 0),
            )
        return AiFeedbackAggregate(
            correct_count=counts.get("correct", 0),
            incorrect_count=counts.get("incorrect", 0),
            uncertain_count=counts.get("uncertain", 0),
        )

    async def copilot_response_in_org(
        self, response_id: UUID, organization_id: UUID
    ) -> DiscoveryCopilotResponseRow | None:
        result = await self._session.execute(
            select(DiscoveryCopilotResponseRow).where(
                DiscoveryCopilotResponseRow.id == str(response_id),
                DiscoveryCopilotResponseRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def audience_hypothesis_in_org(
        self, hypothesis_id: UUID, organization_id: UUID
    ) -> tuple[AudienceHypothesisRow | None, EventRow | None]:
        result = await self._session.execute(
            select(AudienceHypothesisRow).where(AudienceHypothesisRow.id == str(hypothesis_id))
        )
        hyp = result.scalar_one_or_none()
        if hyp is None or hyp.superseded_at is not None:
            return None, None
        ev = await self._session.execute(
            select(EventRow).where(
                EventRow.id == hyp.event_id,
                EventRow.organization_id == str(organization_id),
            )
        )
        event = ev.scalar_one_or_none()
        if event is None:
            return hyp, None
        return hyp, event