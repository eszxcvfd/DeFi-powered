"""Scoring suggestion application service (US-039)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService, make_actor_from_role, make_context
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.domain.campaigns.models import ScoringWeights
from livelead.domain.scoring_suggestions.generator import generate_scoring_suggestions
from livelead.domain.scoring_suggestions.models import ScoringSuggestionStatus
from livelead.domain.scoring_suggestions.validation import (
    ScoringSuggestionValidationError,
    assert_may_decide,
    validate_suggestion_deltas,
)
from livelead.infrastructure.db.mappers import row_to_campaign, weights_to_json
from livelead.infrastructure.db.models import CampaignRow, CampaignScoringWeightSnapshotRow
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.scoring_suggestions import (
    ScoringSuggestionRepository,
    new_suggestion_row,
)


NOTE_MAX_LEN = 500


class ScoringSuggestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ScoringSuggestionRepository(session)
        self._campaigns = CampaignRepository(session)

    async def generate(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        actor_role: str,
    ):
        campaign = await self._campaigns.get(campaign_id, organization_id)
        if not campaign:
            raise ScoringSuggestionValidationError("campaign not found")

        rollup = await self._repo.campaign_feedback_rollup(organization_id, campaign_id)
        result = generate_scoring_suggestions(
            current=campaign.scoring_weights,
            rollup=rollup,
        )
        if result is None:
            raise ScoringSuggestionValidationError(
                "not enough campaign feedback to generate scoring suggestions"
            )

        current_map = dict(campaign.scoring_weights.normalized().weights)
        row = new_suggestion_row(
            organization_id=organization_id,
            campaign_id=campaign_id,
            confidence=result.confidence,
            summary=result.summary,
            caution_notes=result.caution_notes,
            assumptions=result.assumptions,
            signals=result.signals,
            deltas=result.deltas,
            current_weights=current_map,
            proposed_weights=dict(result.proposed_weights),
            generated_by=actor_role,
        )
        return await self._repo.add_set(row)

    async def list_history(self, organization_id: UUID, campaign_id: UUID):
        campaign = await self._campaigns.get(campaign_id, organization_id)
        if not campaign:
            raise ScoringSuggestionValidationError("campaign not found")
        return await self._repo.list_for_campaign(organization_id, campaign_id)

    async def approve(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        suggestion_id: UUID,
        actor_role: str,
    ):
        row = await self._get_pending(suggestion_id, organization_id, campaign_id)
        proposed_raw = json.loads(row.proposed_weights_json or "{}")
        campaign = await self._campaigns.get(campaign_id, organization_id)
        assert campaign is not None
        weights, _ = validate_suggestion_deltas(campaign.scoring_weights, proposed_raw)

        camp_row = await self._campaign_row(campaign_id, organization_id)
        prior_json = camp_row.scoring_weights_json

        snapshot = CampaignScoringWeightSnapshotRow(
            organization_id=str(organization_id),
            campaign_id=str(campaign_id),
            weights_json=weights_to_json(weights),
            source="scoring_suggestion_approved",
            suggestion_set_id=row.id,
            created_by=actor_role,
            created_at=datetime.now(UTC),
        )
        snapshot = await self._repo.add_snapshot(snapshot)

        camp_row.scoring_weights_json = weights_to_json(weights)
        camp_row.updated_at = datetime.now(UTC)
        await self._session.flush()

        row.status = ScoringSuggestionStatus.APPROVED.value
        row.decided_by = actor_role
        row.decided_at = datetime.now(UTC)
        row.weight_snapshot_id = snapshot.id
        await self._session.flush()

        await AuditService(self._session).emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role),
            action=AuditAction.SCORING_SUGGESTION_APPROVED,
            target=AuditTarget(
                target_type=AuditTargetType.SCORING_SUGGESTION_SET,
                target_id=row.id,
                display=f"scoring_suggestion/{row.id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="scoring_suggestions"),
            metadata={
                "campaign_id": str(campaign_id),
                "weight_snapshot_id": snapshot.id,
                "prior_weights_json": prior_json,
            },
        )
        return row, row_to_campaign(camp_row)

    async def reject(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        suggestion_id: UUID,
        actor_role: str,
        review_note: str | None,
    ):
        row = await self._get_pending(suggestion_id, organization_id, campaign_id)
        note = _normalize_note(review_note)
        row.status = ScoringSuggestionStatus.REJECTED.value
        row.decided_by = actor_role
        row.decided_at = datetime.now(UTC)
        row.review_note = note
        await self._session.flush()

        await AuditService(self._session).emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role),
            action=AuditAction.SCORING_SUGGESTION_REJECTED,
            target=AuditTarget(
                target_type=AuditTargetType.SCORING_SUGGESTION_SET,
                target_id=row.id,
                display=f"scoring_suggestion/{row.id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="scoring_suggestions"),
            metadata={"campaign_id": str(campaign_id), "review_note": note},
        )
        return row

    async def _get_pending(
        self, suggestion_id: UUID, organization_id: UUID, campaign_id: UUID
    ):
        row = await self._repo.get(suggestion_id, organization_id, campaign_id)
        if not row:
            raise ScoringSuggestionValidationError("scoring suggestion not found")
        assert_may_decide(row.status)
        return row

    async def _campaign_row(self, campaign_id: UUID, organization_id: UUID) -> CampaignRow:
        result = await self._session.execute(
            select(CampaignRow).where(
                CampaignRow.id == str(campaign_id),
                CampaignRow.organization_id == str(organization_id),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ScoringSuggestionValidationError("campaign not found")
        return row


def _normalize_note(note: str | None) -> str | None:
    if note is None:
        return None
    text = str(note).strip()
    if not text:
        return None
    if len(text) > NOTE_MAX_LEN:
        raise ScoringSuggestionValidationError(f"review_note must be at most {NOTE_MAX_LEN} characters")
    return text