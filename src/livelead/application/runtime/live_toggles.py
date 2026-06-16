"""Live-toggle application service (US-040).

Encapsulates the live-integration toggle state machine. The service
relies on the runtime cutover repositories and emits audit events
through the `AuditService` for every transition. The service is the
only place in the product layer that mutates `LiveIntegrationToggleRow`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.identity import Role
from livelead.domain.runtime.enums import (
    EnvironmentMode,
    LiveIntegration,
    LiveToggleState,
)
from livelead.domain.runtime.gate import summarize_gate
from livelead.domain.runtime.models import (
    LaunchGateReport,
    LiveIntegrationToggle,
)
from livelead.infrastructure.db.repositories.runtime import (
    LiveIntegrationToggleRepository,
)
from livelead.runtime.settings import AppSettings


class LiveToggleValidationError(ValueError):
    """Raised when a toggle transition is rejected by the policy guardrails."""


@dataclass(frozen=True, slots=True)
class LiveToggleTransitionResult:
    toggle: LiveIntegrationToggle
    gate: LaunchGateReport
    accepted: bool
    reason: str = ""


GateProvider = Callable[[], Awaitable[LaunchGateReport]]


class LiveToggleService:
    def __init__(
        self,
        session,
        *,
        audit_service: AuditService,
        settings: AppSettings,
        environment_mode: EnvironmentMode,
        gate_provider: GateProvider,
    ) -> None:
        self._session = session
        self._audit = audit_service
        self._settings = settings
        self._mode = environment_mode
        self._repo = LiveIntegrationToggleRepository(session)
        self._gate_provider = gate_provider

    # -- Read side -----------------------------------------------------------

    async def list_toggles(
        self, organization_id: UUID
    ) -> list[LiveIntegrationToggle]:
        return await self._repo.list_for_org(organization_id)

    async def get_toggle(
        self, organization_id: UUID, integration: LiveIntegration
    ) -> LiveIntegrationToggle:
        existing = await self._repo.get(organization_id, integration)
        if existing is not None:
            return existing
        return LiveIntegrationToggle(
            integration=integration,
            state=LiveToggleState.DISABLED,
        )

    # -- Write side ----------------------------------------------------------

    async def enable(
        self,
        *,
        organization_id: UUID,
        integration: LiveIntegration,
        actor: str,
        actor_role: str,
        approval_note: str,
    ) -> LiveToggleTransitionResult:
        if not approval_note or not approval_note.strip():
            raise LiveToggleValidationError("approval_note is required to enable a live toggle")
        if not _is_admin_role(actor_role):
            raise LiveToggleValidationError("admin or owner role required to enable a live toggle")

        gate = await self._gate_provider()
        if self._mode != EnvironmentMode.PILOT_LIVE:
            await self._record_audit(
                organization_id=organization_id,
                integration=integration,
                actor=actor,
                actor_role=actor_role,
                outcome=AuditOutcome.DENIED,
                new_state=LiveToggleState.ENABLED,
                note=approval_note,
                gate=gate,
                reason=(
                    f"environment is {self._mode.value}; pilot_live required to enable"
                ),
            )
            raise LiveToggleValidationError(
                f"environment must be pilot_live to enable {integration.value}"
            )
        if not gate.passed:
            summary = summarize_gate(gate)
            await self._record_audit(
                organization_id=organization_id,
                integration=integration,
                actor=actor,
                actor_role=actor_role,
                outcome=AuditOutcome.DENIED,
                new_state=LiveToggleState.ENABLED,
                note=approval_note,
                gate=gate,
                reason=summary,
            )
            raise LiveToggleValidationError(f"launch gate blocks live enable: {summary}")

        toggle = await self._repo.upsert(
            organization_id,
            integration,
            new_state=LiveToggleState.ENABLED,
            actor=actor,
            approval_note=approval_note,
        )
        await self._record_audit(
            organization_id=organization_id,
            integration=integration,
            actor=actor,
            actor_role=actor_role,
            outcome=AuditOutcome.SUCCEEDED,
            new_state=LiveToggleState.ENABLED,
            note=approval_note,
            gate=gate,
            reason="live toggle enabled",
        )
        return LiveToggleTransitionResult(
            toggle=toggle,
            gate=gate,
            accepted=True,
            reason="enabled",
        )

    async def disable(
        self,
        *,
        organization_id: UUID,
        integration: LiveIntegration,
        actor: str,
        actor_role: str,
        reason: str,
    ) -> LiveToggleTransitionResult:
        if not _is_admin_role(actor_role):
            raise LiveToggleValidationError("admin or owner role required to disable a live toggle")
        if not reason or not reason.strip():
            raise LiveToggleValidationError("reason is required to disable a live toggle")

        gate = await self._gate_provider()
        toggle = await self._repo.upsert(
            organization_id,
            integration,
            new_state=LiveToggleState.DISABLED,
            actor=actor,
            approval_note=reason,
        )
        await self._record_audit(
            organization_id=organization_id,
            integration=integration,
            actor=actor,
            actor_role=actor_role,
            outcome=AuditOutcome.SUCCEEDED,
            new_state=LiveToggleState.DISABLED,
            note=reason,
            gate=gate,
            reason="live toggle disabled",
        )
        return LiveToggleTransitionResult(
            toggle=toggle,
            gate=gate,
            accepted=True,
            reason="disabled",
        )

    # -- Audit helper --------------------------------------------------------

    async def _record_audit(
        self,
        *,
        organization_id: UUID,
        integration: LiveIntegration,
        actor: str,
        actor_role: str,
        outcome: AuditOutcome,
        new_state: LiveToggleState,
        note: str,
        gate: LaunchGateReport,
        reason: str,
    ) -> None:
        metadata: dict[str, Any] = {
            "integration": integration.value,
            "new_state": new_state.value,
            "environment_mode": gate.environment_mode.value,
            "gate_passed": gate.passed,
            "approval_note": note,
            "reason": reason,
        }
        if not gate.passed:
            metadata["blocking"] = [
                {"name": c.name, "detail": c.detail} for c in gate.blocking_checks
            ]
        audit_actor = make_actor_from_role(actor_role, actor_id=actor or actor_role)
        await self._audit.emit(
            organization_id=organization_id,
            actor=audit_actor,
            action=AuditAction.ENVIRONMENT_TOGGLE_CHANGED,
            target=AuditTarget(
                target_type=AuditTargetType.LIVE_INTEGRATION_TOGGLE,
                target_id=integration.value,
                display=f"live_integration_toggle:{integration.value}",
            ),
            outcome=outcome,
            context=make_context(workflow="live_toggle"),
            metadata=metadata,
        )


def _is_admin_role(role: str | None) -> bool:
    if not role:
        return False
    try:
        r = Role(str(role).strip().lower())
    except ValueError:
        return False
    return r in (Role.OWNER, Role.ADMIN)
