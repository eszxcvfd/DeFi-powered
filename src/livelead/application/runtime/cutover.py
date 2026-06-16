"""Cutover application service (US-040).

Owns the live-mode state machine: `enter_pilot_live`, `pause`, and
`rollback`. Every transition records a `CutoverEvent` and emits an
audit entry. The launch gate must pass for `enter_pilot_live` to
succeed; `pause` is always allowed; `rollback` returns the
environment to `test_like` (or `paused`) and disables all live
toggles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

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
    CutoverAction,
    EnvironmentMode,
    LiveIntegration,
)
from livelead.domain.runtime.gate import summarize_gate
from livelead.domain.runtime.models import (
    CutoverEvent,
    LaunchGateReport,
)
from livelead.infrastructure.db.repositories.runtime import (
    CutoverEventRepository,
    LiveIntegrationToggleRepository,
)
from livelead.runtime.settings import AppSettings


class CutoverError(ValueError):
    """Raised when a cutover transition is rejected."""


@dataclass(frozen=True, slots=True)
class CutoverResult:
    event: CutoverEvent
    previous_mode: EnvironmentMode
    new_mode: EnvironmentMode
    gate: LaunchGateReport


GateProvider = Callable[[], Awaitable[LaunchGateReport]]
BackupCountProvider = Callable[[], Awaitable[int]]
ModeProvider = Callable[[], EnvironmentMode]


class CutoverService:
    def __init__(
        self,
        session,
        *,
        audit_service: AuditService,
        settings: AppSettings,
        current_mode_provider: ModeProvider,
        gate_provider: GateProvider,
        backup_count_provider: BackupCountProvider,
        on_mode_change: Callable[[EnvironmentMode], None] | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service
        self._settings = settings
        self._current_mode_provider = current_mode_provider
        self._gate_provider = gate_provider
        self._backup_count_provider = backup_count_provider
        self._on_mode_change = on_mode_change
        self._events = CutoverEventRepository(session)
        self._toggles = LiveIntegrationToggleRepository(session)

    async def enter_pilot_live(
        self,
        *,
        organization_id: UUID,
        actor: str,
        actor_role: str,
        reason: str,
        notes: str = "",
        admin_pin: str | None = None,
    ) -> CutoverResult:
        if not _is_admin_role(actor_role):
            raise CutoverError("admin or owner role required to enter pilot_live")
        if not reason or not reason.strip():
            raise CutoverError("reason is required to enter pilot_live")
        if self._settings.pilot_live_admin_pin:
            if not admin_pin or admin_pin != self._settings.pilot_live_admin_pin:
                raise CutoverError("admin pin mismatch; live cutover aborted")

        previous_mode = self._current_mode_provider()
        gate = await self._gate_provider()

        if not gate.passed:
            summary = summarize_gate(gate)
            await self._record_audit(
                organization_id=organization_id,
                action=CutoverAction.ENTER_PILOT_LIVE,
                actor=actor,
                actor_role=actor_role,
                outcome=AuditOutcome.DENIED,
                previous_mode=previous_mode,
                new_mode=EnvironmentMode.PILOT_LIVE,
                reason=reason,
                notes=notes,
                gate=gate,
                summary=summary,
            )
            raise CutoverError(f"launch gate blocked: {summary}")

        backups = await self._backup_count_provider()
        if backups < int(self._settings.launch_gate_min_backup_count or 0):
            await self._record_audit(
                organization_id=organization_id,
                action=CutoverAction.ENTER_PILOT_LIVE,
                actor=actor,
                actor_role=actor_role,
                outcome=AuditOutcome.DENIED,
                previous_mode=previous_mode,
                new_mode=EnvironmentMode.PILOT_LIVE,
                reason=reason,
                notes=notes,
                gate=gate,
                summary=(
                    f"need at least {self._settings.launch_gate_min_backup_count} "
                    f"backup snapshot(s); found {backups}"
                ),
            )
            raise CutoverError(
                f"at least {self._settings.launch_gate_min_backup_count} backup "
                f"snapshot(s) required; found {backups}"
            )

        event = await self._record_event(
            action=CutoverAction.ENTER_PILOT_LIVE,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PILOT_LIVE,
            actor=actor,
            reason=reason,
            notes=notes,
            gate=gate,
        )
        if self._on_mode_change is not None:
            self._on_mode_change(EnvironmentMode.PILOT_LIVE)
        await self._record_audit(
            organization_id=organization_id,
            action=CutoverAction.ENTER_PILOT_LIVE,
            actor=actor,
            actor_role=actor_role,
            outcome=AuditOutcome.SUCCEEDED,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PILOT_LIVE,
            reason=reason,
            notes=notes,
            gate=gate,
            summary="enter_pilot_live accepted",
        )
        return CutoverResult(
            event=event,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PILOT_LIVE,
            gate=gate,
        )

    async def pause(
        self,
        *,
        organization_id: UUID,
        actor: str,
        actor_role: str,
        reason: str,
        notes: str = "",
    ) -> CutoverResult:
        if not _is_admin_role(actor_role):
            raise CutoverError("admin or owner role required to pause")
        if not reason or not reason.strip():
            raise CutoverError("reason is required to pause")
        previous_mode = self._current_mode_provider()
        gate = await self._gate_provider()
        event = await self._record_event(
            action=CutoverAction.PAUSE,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PAUSED,
            actor=actor,
            reason=reason,
            notes=notes,
            gate=gate,
        )
        # Pause disables all currently-enabled live toggles.
        await self._toggles.disable_all_for_org(organization_id, actor=actor)
        if self._on_mode_change is not None:
            self._on_mode_change(EnvironmentMode.PAUSED)
        await self._record_audit(
            organization_id=organization_id,
            action=CutoverAction.PAUSE,
            actor=actor,
            actor_role=actor_role,
            outcome=AuditOutcome.SUCCEEDED,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PAUSED,
            reason=reason,
            notes=notes,
            gate=gate,
            summary="environment paused; live toggles disabled",
        )
        return CutoverResult(
            event=event,
            previous_mode=previous_mode,
            new_mode=EnvironmentMode.PAUSED,
            gate=gate,
        )

    async def rollback(
        self,
        *,
        organization_id: UUID,
        actor: str,
        actor_role: str,
        reason: str,
        notes: str = "",
        target_mode: EnvironmentMode = EnvironmentMode.TEST_LIKE,
    ) -> CutoverResult:
        if not _is_admin_role(actor_role):
            raise CutoverError("admin or owner role required to rollback")
        if not reason or not reason.strip():
            raise CutoverError("reason is required to rollback")
        if target_mode == EnvironmentMode.PILOT_LIVE:
            raise CutoverError("rollback must return to test_like or paused")
        previous_mode = self._current_mode_provider()
        gate = await self._gate_provider()
        await self._toggles.disable_all_for_org(organization_id, actor=actor)
        if self._on_mode_change is not None:
            self._on_mode_change(target_mode)
        event = await self._record_event(
            action=CutoverAction.ROLLBACK,
            previous_mode=previous_mode,
            new_mode=target_mode,
            actor=actor,
            reason=reason,
            notes=notes,
            gate=gate,
        )
        await self._record_audit(
            organization_id=organization_id,
            action=CutoverAction.ROLLBACK,
            actor=actor,
            actor_role=actor_role,
            outcome=AuditOutcome.SUCCEEDED,
            previous_mode=previous_mode,
            new_mode=target_mode,
            reason=reason,
            notes=notes,
            gate=gate,
            summary=f"rollback to {target_mode.value}; live toggles disabled",
        )
        return CutoverResult(
            event=event,
            previous_mode=previous_mode,
            new_mode=target_mode,
            gate=gate,
        )

    async def list_events(self, *, limit: int = 20) -> list[CutoverEvent]:
        return await self._events.list_recent(limit=limit)

    # -- Internals -----------------------------------------------------------

    async def _record_event(
        self,
        *,
        action: CutoverAction,
        previous_mode: EnvironmentMode,
        new_mode: EnvironmentMode,
        actor: str,
        reason: str,
        notes: str,
        gate: LaunchGateReport,
    ) -> CutoverEvent:
        event = CutoverEvent(
            event_id=str(uuid4()),
            action=action,
            previous_mode=previous_mode,
            new_mode=new_mode,
            actor=actor or "",
            reason=reason or "",
            occurred_at=datetime.now(UTC),
            notes=notes or "",
            gate_passed=gate.passed,
            gate_summary=summarize_gate(gate),
        )
        return await self._events.add(event)

    async def _record_audit(
        self,
        *,
        organization_id: UUID,
        action: CutoverAction,
        actor: str,
        actor_role: str,
        outcome: AuditOutcome,
        previous_mode: EnvironmentMode,
        new_mode: EnvironmentMode,
        reason: str,
        notes: str,
        gate: LaunchGateReport,
        summary: str,
    ) -> None:
        metadata: dict[str, Any] = {
            "cutover_action": action.value,
            "previous_mode": previous_mode.value,
            "new_mode": new_mode.value,
            "reason": reason,
            "notes": notes,
            "gate_passed": gate.passed,
            "summary": summary,
        }
        if not gate.passed:
            metadata["blocking"] = [
                {"name": c.name, "detail": c.detail} for c in gate.blocking_checks
            ]
        audit_actor = make_actor_from_role(actor_role, actor_id=actor or actor_role)
        audit_action = {
            CutoverAction.ENTER_PILOT_LIVE: AuditAction.ENVIRONMENT_MODE_CHANGED,
            CutoverAction.PAUSE: AuditAction.ENVIRONMENT_PAUSED,
            CutoverAction.ROLLBACK: AuditAction.ENVIRONMENT_ROLLED_BACK,
        }[action]
        await self._audit.emit(
            organization_id=organization_id,
            actor=audit_actor,
            action=audit_action,
            target=AuditTarget(
                target_type=AuditTargetType.ENVIRONMENT,
                target_id=new_mode.value,
                display=f"environment:{new_mode.value}",
            ),
            outcome=outcome,
            context=make_context(workflow="cutover"),
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
