"""AI feedback application service (US-038)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService, make_actor_from_role, make_context
from livelead.domain.ai_feedback.models import AiFeedbackProjection, AiFeedbackTargetType
from livelead.domain.ai_feedback.validation import (
    assert_no_auto_learning_side_effect,
    validate_audience_hypothesis_feedback,
    validate_discovery_copilot_feedback,
)
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.infrastructure.db.repositories.ai_feedback import AiFeedbackRepository


class AiFeedbackValidationError(ValueError):
    pass


def resolve_feedback_actor_key(*, actor_id: str, actor_role: str) -> str:
    if actor_id and actor_id.strip():
        return actor_id.strip()
    role = (actor_role or "viewer").strip().lower() or "viewer"
    return f"dev:{role}"


class AiFeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AiFeedbackRepository(session)

    async def record_discovery_copilot_feedback(
        self,
        *,
        organization_id: UUID,
        response_id: UUID,
        actor_key: str,
        actor_role: str,
        state: str,
        reason_code: str | None,
        note: str | None,
    ) -> AiFeedbackProjection:
        assert_no_auto_learning_side_effect("persist_feedback_only")
        try:
            eff_state, eff_reason, eff_note = validate_discovery_copilot_feedback(
                state=state, reason_code=reason_code, note=note
            )
        except ValueError as exc:
            raise AiFeedbackValidationError(str(exc)) from exc

        row = await self._repo.copilot_response_in_org(response_id, organization_id)
        if row is None:
            raise AiFeedbackValidationError("copilot response not found")

        prior = await self._repo.get_viewer_projection(
            organization_id,
            actor_key,
            AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE,
            response_id,
        )
        await self._repo.append(
            organization_id=organization_id,
            target_type=AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE,
            target_id=response_id,
            actor_key=actor_key,
            state=eff_state,
            reason_code=eff_reason,
            note=eff_note,
            prior_state=prior.state if prior else None,
        )
        await AuditService(self._session).emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor_key),
            action=AuditAction.AI_FEEDBACK_RECORDED,
            target=AuditTarget(
                target_type=AuditTargetType.DISCOVERY_COPILOT_RESPONSE,
                target_id=str(response_id),
                display=f"discovery_copilot/{response_id}/feedback",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="ai_feedback"),
            metadata={
                "target_type": AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE.value,
                "state": eff_state,
                "reason_code": eff_reason,
                "prior_state": prior.state if prior else None,
            },
        )
        proj = await self._repo.get_viewer_projection(
            organization_id,
            actor_key,
            AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE,
            response_id,
        )
        assert proj is not None
        return proj

    async def record_audience_hypothesis_feedback(
        self,
        *,
        organization_id: UUID,
        hypothesis_id: UUID,
        actor_key: str,
        actor_role: str,
        state: str,
        reason_code: str | None,
        note: str | None,
    ) -> AiFeedbackProjection:
        assert_no_auto_learning_side_effect("persist_feedback_only")
        try:
            eff_state, eff_reason, eff_note = validate_audience_hypothesis_feedback(
                state=state, reason_code=reason_code, note=note
            )
        except ValueError as exc:
            raise AiFeedbackValidationError(str(exc)) from exc

        hyp, event = await self._repo.audience_hypothesis_in_org(hypothesis_id, organization_id)
        if hyp is None or event is None:
            raise AiFeedbackValidationError("audience hypothesis not found")

        prior = await self._repo.get_viewer_projection(
            organization_id,
            actor_key,
            AiFeedbackTargetType.AUDIENCE_HYPOTHESIS,
            hypothesis_id,
        )
        await self._repo.append(
            organization_id=organization_id,
            target_type=AiFeedbackTargetType.AUDIENCE_HYPOTHESIS,
            target_id=hypothesis_id,
            actor_key=actor_key,
            state=eff_state,
            reason_code=eff_reason,
            note=eff_note,
            prior_state=prior.state if prior else None,
        )
        await AuditService(self._session).emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor_key),
            action=AuditAction.AI_FEEDBACK_RECORDED,
            target=AuditTarget(
                target_type=AuditTargetType.AUDIENCE_HYPOTHESIS,
                target_id=str(hypothesis_id),
                display=f"audience_hypothesis/{hypothesis_id}/feedback",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="ai_feedback"),
            metadata={
                "target_type": AiFeedbackTargetType.AUDIENCE_HYPOTHESIS.value,
                "state": eff_state,
                "reason_code": eff_reason,
                "prior_state": prior.state if prior else None,
                "event_id": event.id,
            },
        )
        proj = await self._repo.get_viewer_projection(
            organization_id,
            actor_key,
            AiFeedbackTargetType.AUDIENCE_HYPOTHESIS,
            hypothesis_id,
        )
        assert proj is not None
        return proj

    async def get_viewer_projection(
        self,
        organization_id: UUID,
        actor_key: str,
        target_type: AiFeedbackTargetType,
        target_id: UUID,
    ) -> AiFeedbackProjection | None:
        return await self._repo.get_viewer_projection(
            organization_id, actor_key, target_type, target_id
        )

    async def project_for_viewer(
        self,
        organization_id: UUID,
        actor_key: str,
        target_type: AiFeedbackTargetType,
        target_ids: list[UUID],
    ) -> dict[UUID, AiFeedbackProjection]:
        return await self._repo.project_for_viewer(
            organization_id, actor_key, target_type, target_ids
        )