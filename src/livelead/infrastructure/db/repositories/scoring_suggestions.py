"""Scoring suggestion persistence (US-039)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.ai_feedback.models import AiFeedbackTargetType
from livelead.domain.scoring_suggestions.generator import CampaignFeedbackRollup
from livelead.domain.scoring_suggestions.models import (
    ScoringSuggestionSignal,
    ScoringSuggestionSignalKind,
    ScoringWeightDelta,
)
from livelead.infrastructure.db.models import (
    AiFeedbackEventRow,
    AudienceHypothesisRow,
    CampaignScoringWeightSnapshotRow,
    DiscoveryCopilotResponseRow,
    EventRow,
    ScoringSuggestionSetRow,
)


def signals_to_json(signals: tuple[ScoringSuggestionSignal, ...]) -> str:
    return json.dumps(
        [
            {
                "kind": s.kind.value,
                "summary": s.summary,
                "count": s.count,
                "reason_code": s.reason_code,
            }
            for s in signals
        ]
    )


def signals_from_json(raw: str) -> tuple[ScoringSuggestionSignal, ...]:
    data = json.loads(raw or "[]")
    out: list[ScoringSuggestionSignal] = []
    for item in data:
        try:
            kind = ScoringSuggestionSignalKind(item.get("kind", ""))
        except ValueError:
            continue
        out.append(
            ScoringSuggestionSignal(
                kind=kind,
                summary=str(item.get("summary", "")),
                count=int(item.get("count", 0)),
                reason_code=item.get("reason_code"),
            )
        )
    return tuple(out)


def deltas_to_json(deltas: tuple[ScoringWeightDelta, ...]) -> str:
    return json.dumps(
        [
            {
                "component": d.component,
                "current_weight": d.current_weight,
                "proposed_weight": d.proposed_weight,
                "rationale": d.rationale,
            }
            for d in deltas
        ]
    )


def deltas_from_json(raw: str) -> tuple[ScoringWeightDelta, ...]:
    data = json.loads(raw or "[]")
    return tuple(
        ScoringWeightDelta(
            component=str(item.get("component", "")),
            current_weight=float(item.get("current_weight", 0)),
            proposed_weight=float(item.get("proposed_weight", 0)),
            rationale=str(item.get("rationale", "")),
        )
        for item in data
    )


class ScoringSuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_campaign(
        self,
        organization_id: UUID,
        campaign_id: UUID,
        *,
        limit: int = 20,
    ) -> list[ScoringSuggestionSetRow]:
        result = await self._session.execute(
            select(ScoringSuggestionSetRow)
            .where(
                ScoringSuggestionSetRow.organization_id == str(organization_id),
                ScoringSuggestionSetRow.campaign_id == str(campaign_id),
            )
            .order_by(ScoringSuggestionSetRow.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get(
        self,
        suggestion_id: UUID,
        organization_id: UUID,
        campaign_id: UUID,
    ) -> ScoringSuggestionSetRow | None:
        result = await self._session.execute(
            select(ScoringSuggestionSetRow).where(
                ScoringSuggestionSetRow.id == str(suggestion_id),
                ScoringSuggestionSetRow.organization_id == str(organization_id),
                ScoringSuggestionSetRow.campaign_id == str(campaign_id),
            )
        )
        return result.scalar_one_or_none()

    async def add_set(self, row: ScoringSuggestionSetRow) -> ScoringSuggestionSetRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_snapshot(
        self, row: CampaignScoringWeightSnapshotRow
    ) -> CampaignScoringWeightSnapshotRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def campaign_feedback_rollup(
        self, organization_id: UUID, campaign_id: UUID
    ) -> CampaignFeedbackRollup:
        org = str(organization_id)
        cid = str(campaign_id)

        aud_incorrect = await self._count_audience_state(org, cid, "incorrect")
        aud_wrong_fit = await self._count_audience_reason(org, cid, "wrong_audience_fit")
        aud_uncertain = await self._count_audience_state(org, cid, "uncertain")

        copilot_not = await self._count_copilot_state(org, cid, "not_helpful")
        copilot_help = await self._count_copilot_state(org, cid, "helpful")

        return CampaignFeedbackRollup(
            audience_incorrect=aud_incorrect,
            audience_wrong_fit=aud_wrong_fit,
            audience_uncertain=aud_uncertain,
            copilot_not_helpful=copilot_not,
            copilot_helpful=copilot_help,
        )

    async def _count_audience_state(self, org: str, campaign_id: str, state: str) -> int:
        subq = (
            select(
                AiFeedbackEventRow.target_id,
                func.max(AiFeedbackEventRow.created_at).label("max_at"),
            )
            .join(
                AudienceHypothesisRow,
                AudienceHypothesisRow.id == AiFeedbackEventRow.target_id,
            )
            .join(EventRow, EventRow.id == AudienceHypothesisRow.event_id)
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.target_type == AiFeedbackTargetType.AUDIENCE_HYPOTHESIS.value,
                EventRow.organization_id == org,
                EventRow.campaign_id == campaign_id,
                AudienceHypothesisRow.superseded_at.is_(None),
            )
            .group_by(AiFeedbackEventRow.target_id)
            .subquery()
        )
        result = await self._session.execute(
            select(func.count())
            .select_from(AiFeedbackEventRow)
            .join(
                subq,
                (AiFeedbackEventRow.target_id == subq.c.target_id)
                & (AiFeedbackEventRow.created_at == subq.c.max_at),
            )
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.state == state,
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_audience_reason(self, org: str, campaign_id: str, reason: str) -> int:
        subq = (
            select(
                AiFeedbackEventRow.target_id,
                func.max(AiFeedbackEventRow.created_at).label("max_at"),
            )
            .join(
                AudienceHypothesisRow,
                AudienceHypothesisRow.id == AiFeedbackEventRow.target_id,
            )
            .join(EventRow, EventRow.id == AudienceHypothesisRow.event_id)
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.target_type == AiFeedbackTargetType.AUDIENCE_HYPOTHESIS.value,
                EventRow.organization_id == org,
                EventRow.campaign_id == campaign_id,
                AudienceHypothesisRow.superseded_at.is_(None),
            )
            .group_by(AiFeedbackEventRow.target_id)
            .subquery()
        )
        result = await self._session.execute(
            select(func.count())
            .select_from(AiFeedbackEventRow)
            .join(
                subq,
                (AiFeedbackEventRow.target_id == subq.c.target_id)
                & (AiFeedbackEventRow.created_at == subq.c.max_at),
            )
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.state == "incorrect",
                AiFeedbackEventRow.reason_code == reason,
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_copilot_state(self, org: str, campaign_id: str, state: str) -> int:
        subq = (
            select(
                AiFeedbackEventRow.target_id,
                func.max(AiFeedbackEventRow.created_at).label("max_at"),
            )
            .join(
                DiscoveryCopilotResponseRow,
                DiscoveryCopilotResponseRow.id == AiFeedbackEventRow.target_id,
            )
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.target_type
                == AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE.value,
                DiscoveryCopilotResponseRow.organization_id == org,
                DiscoveryCopilotResponseRow.campaign_id == campaign_id,
            )
            .group_by(AiFeedbackEventRow.target_id)
            .subquery()
        )
        result = await self._session.execute(
            select(func.count())
            .select_from(AiFeedbackEventRow)
            .join(
                subq,
                (AiFeedbackEventRow.target_id == subq.c.target_id)
                & (AiFeedbackEventRow.created_at == subq.c.max_at),
            )
            .where(
                AiFeedbackEventRow.organization_id == org,
                AiFeedbackEventRow.state == state,
            )
        )
        return int(result.scalar_one() or 0)


def new_suggestion_row(
    *,
    organization_id: UUID,
    campaign_id: UUID,
    confidence: float,
    summary: str,
    caution_notes: tuple[str, ...],
    assumptions: tuple[str, ...],
    signals: tuple[ScoringSuggestionSignal, ...],
    deltas: tuple[ScoringWeightDelta, ...],
    current_weights: dict[str, float],
    proposed_weights: dict[str, float],
    generated_by: str,
) -> ScoringSuggestionSetRow:
    return ScoringSuggestionSetRow(
        id=str(uuid4()),
        organization_id=str(organization_id),
        campaign_id=str(campaign_id),
        status="pending_review",
        confidence=confidence,
        summary=summary,
        caution_notes_json=json.dumps(list(caution_notes)),
        assumptions_json=json.dumps(list(assumptions)),
        signals_json=signals_to_json(signals),
        deltas_json=deltas_to_json(deltas),
        current_weights_json=json.dumps(current_weights),
        proposed_weights_json=json.dumps(proposed_weights),
        generated_by=generated_by,
        created_at=datetime.now(UTC),
    )