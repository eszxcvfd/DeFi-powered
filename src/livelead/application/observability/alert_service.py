"""Alert management application service (US-041).

Owns the rule CRUD, the acknowledge/resolve lifecycle, and the
operator summary endpoint. The service is intentionally synchronous
in shape: the evaluator runs the same service in a worker tick
and the management API runs it from request handlers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.observability.signals import SignalProviderFactory
from livelead.application.runtime.readiness import RuntimeReadinessService
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditActor, AuditTarget
from livelead.domain.observability.enums import (
    AlertChannel,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from livelead.domain.observability.models import (
    AlertEvent,
    AlertRule,
    apply_rule_grammar,
    validate_rule_payload,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.infrastructure.db.models import OrganizationMembershipRow
from livelead.infrastructure.db.repositories.observability import (
    AlertEventRepository,
    AlertRuleRepository,
)
from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.observability_service")


class AlertRuleValidationError(ValueError):
    """Raised when a rule payload fails the closed grammar."""


class AlertRuleNotFound(LookupError):
    pass


class AlertEventNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class AlertRuleListView:
    items: list[AlertRule]


@dataclass(frozen=True, slots=True)
class AlertEventListView:
    items: list[AlertEvent]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class OperatorSummary:
    environment_mode: str
    gate_passed: bool
    gate_blocking: tuple[dict[str, str], ...]
    gate_warnings: tuple[dict[str, str], ...]
    backup_freshness: str
    backup_age_hours: float | None
    worker_heartbeat_age_seconds: float | None
    open_alerts_by_severity: dict[str, int]
    recent_alerts: list[AlertEvent]
    rules_total: int
    rules_enabled: int


class AlertService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        signal_factory: SignalProviderFactory | None = None,
    ) -> None:
        self._session = session
        self._rules = AlertRuleRepository(session)
        self._events = AlertEventRepository(session)
        self._audit = audit_service or AuditService(session)
        self._signal_factory = signal_factory or SignalProviderFactory()

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def signal_factory(self) -> SignalProviderFactory:
        return self._signal_factory

    @property
    def rule_repo(self) -> AlertRuleRepository:
        return self._rules

    @property
    def event_repo(self) -> AlertEventRepository:
        return self._events

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------
    async def create_rule(
        self,
        *,
        organization_id: UUID | str,
        name: str,
        metric: AlertMetric | str,
        operator: AlertOperator | str,
        threshold: float,
        window_seconds: int,
        severity: AlertSeverity | str,
        cooldown_seconds: int,
        channels: Sequence[AlertChannel | str],
        enabled: bool,
        actor: str,
        actor_role: str,
    ) -> AlertRule:
        try:
            validate_rule_payload(
                name=name,
                metric=metric,
                operator=operator,
                threshold=threshold,
                window_seconds=window_seconds,
                severity=severity,
                channels=channels,
                cooldown_seconds=cooldown_seconds,
            )
        except ValueError as exc:
            raise AlertRuleValidationError(str(exc)) from exc
        metric_e, operator_e, channels_e, window_i, threshold_f = apply_rule_grammar(
            metric=metric,
            operator=operator,
            threshold=threshold,
            window_seconds=window_seconds,
            channels=channels,
        )
        severity_e = (
            severity if isinstance(severity, AlertSeverity) else AlertSeverity(str(severity))
        )
        existing = await self._rules.get_by_name(organization_id, name)
        if existing is not None:
            raise AlertRuleValidationError(
                f"ALERT_RULE_DUPLICATE:name_exists:{name}"
            )
        rule = await self._rules.add(
            organization_id=organization_id,
            name=name,
            metric=metric_e,
            operator=operator_e,
            threshold=threshold_f,
            window_seconds=window_i,
            severity=severity_e,
            cooldown_seconds=int(cooldown_seconds),
            channels=channels_e,
            enabled=enabled,
            is_system=False,
            sort_order=200,
            created_by=actor or "system",
        )
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.ALERT_RULE_CREATED,
            target=AuditTarget(
                target_type=AuditTargetType.ALERT_RULE,
                target_id=rule.id,
                display=rule.name,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="alert.rule.create"),
            metadata={
                "rule_id": rule.id,
                "name": rule.name,
                "metric": rule.metric.value,
                "operator": rule.operator.value,
                "threshold": rule.threshold,
                "window_seconds": rule.window_seconds,
                "severity": rule.severity.value,
                "cooldown_seconds": rule.cooldown_seconds,
                "channels": [c.value for c in rule.channels],
            },
        )
        return rule

    async def update_rule(
        self,
        *,
        organization_id: UUID | str,
        rule_id: str,
        actor: str,
        actor_role: str,
        threshold: float | None = None,
        window_seconds: int | None = None,
        severity: AlertSeverity | str | None = None,
        cooldown_seconds: int | None = None,
        channels: Sequence[AlertChannel | str] | None = None,
        enabled: bool | None = None,
    ) -> AlertRule:
        rule = await self._rules.get(rule_id)
        if rule is None or rule.organization_id != str(organization_id):
            raise AlertRuleNotFound(f"alert rule not found: {rule_id}")
        if rule.is_system:
            # System rules can be tuned but the system marker cannot change.
            if threshold is not None and float(threshold) != float(threshold):
                raise AlertRuleValidationError(
                    "ALERT_RULE_INVALID:threshold_nan"
                )
        # Validate the resulting state.
        new_threshold = float(threshold) if threshold is not None else rule.threshold
        new_window = int(window_seconds) if window_seconds is not None else rule.window_seconds
        new_severity = (
            AlertSeverity(severity.value if isinstance(severity, AlertSeverity) else str(severity))
            if severity is not None
            else rule.severity
        )
        new_cooldown = int(cooldown_seconds) if cooldown_seconds is not None else rule.cooldown_seconds
        if channels is not None:
            _, _, new_channels_e, _, _ = apply_rule_grammar(
                metric=rule.metric,
                operator=rule.operator,
                threshold=new_threshold,
                window_seconds=new_window,
                channels=channels,
            )
        else:
            new_channels_e = rule.channels
        try:
            validate_rule_payload(
                name=rule.name,
                metric=rule.metric,
                operator=rule.operator,
                threshold=new_threshold,
                window_seconds=new_window,
                severity=new_severity,
                channels=new_channels_e,
                cooldown_seconds=new_cooldown,
            )
        except ValueError as exc:
            raise AlertRuleValidationError(str(exc)) from exc
        updated = await self._rules.update(
            rule_id=rule.id,
            threshold=threshold,
            window_seconds=window_seconds,
            severity=(
                new_severity if severity is not None else None
            ),
            cooldown_seconds=cooldown_seconds,
            channels=new_channels_e if channels is not None else None,
            enabled=enabled,
        )
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.ALERT_RULE_UPDATED,
            target=AuditTarget(
                target_type=AuditTargetType.ALERT_RULE,
                target_id=updated.id,
                display=updated.name,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="alert.rule.update"),
            metadata={
                "rule_id": updated.id,
                "name": updated.name,
                "threshold": updated.threshold,
                "window_seconds": updated.window_seconds,
                "severity": updated.severity.value,
                "cooldown_seconds": updated.cooldown_seconds,
                "channels": [c.value for c in updated.channels],
                "enabled": updated.enabled,
            },
        )
        return updated

    async def list_rules(
        self, organization_id: UUID | str
    ) -> AlertRuleListView:
        items = await self._rules.list_for_org(organization_id)
        return AlertRuleListView(items=items)

    async def get_rule(
        self, organization_id: UUID | str, rule_id: str
    ) -> AlertRule:
        rule = await self._rules.get(rule_id)
        if rule is None or rule.organization_id != str(organization_id):
            raise AlertRuleNotFound(f"alert rule not found: {rule_id}")
        return rule

    async def delete_rule(
        self,
        *,
        organization_id: UUID | str,
        rule_id: str,
        actor: str,
        actor_role: str,
    ) -> bool:
        rule = await self._rules.get(rule_id)
        if rule is None or rule.organization_id != str(organization_id):
            raise AlertRuleNotFound(f"alert rule not found: {rule_id}")
        if rule.is_system:
            raise AlertRuleValidationError(
                "ALERT_RULE_PROTECTED:system_rule_cannot_be_deleted"
            )
        ok = await self._rules.soft_delete(rule_id)
        if ok:
            await self._audit.emit(
                organization_id=organization_id,
                actor=make_actor_from_role(actor_role, actor_id=actor or None),
                action=AuditAction.ALERT_RULE_DELETED,
                target=AuditTarget(
                    target_type=AuditTargetType.ALERT_RULE,
                    target_id=rule.id,
                    display=rule.name,
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=make_context(workflow="alert.rule.delete"),
                metadata={"rule_id": rule.id, "name": rule.name},
            )
        return ok

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    async def list_events(
        self,
        organization_id: UUID | str,
        *,
        status: AlertEventStatus | str | None = None,
        severity: AlertSeverity | str | None = None,
        rule_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AlertEventListView:
        items, total = await self._events.list_for_org(
            organization_id,
            status=status,
            severity=severity,
            rule_id=rule_id,
            limit=limit,
            offset=offset,
        )
        return AlertEventListView(
            items=items, total=total, limit=limit, offset=offset
        )

    async def acknowledge_event(
        self,
        *,
        organization_id: UUID | str,
        event_id: str,
        actor: str,
        actor_role: str,
    ) -> AlertEvent:
        existing = await self._events.get(event_id)
        if existing is None or existing.organization_id != str(organization_id):
            raise AlertEventNotFound(f"alert event not found: {event_id}")
        updated = await self._events.acknowledge(event_id, actor=actor)
        if updated is None:
            # Was already resolved or acknowledged; return current state.
            return existing
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.ALERT_ACKNOWLEDGED,
            target=AuditTarget(
                target_type=AuditTargetType.ALERT_EVENT,
                target_id=updated.id,
                display=updated.rule_name,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="alert.acknowledge"),
            metadata={
                "event_id": updated.id,
                "rule_id": updated.rule_id,
                "rule_name": updated.rule_name,
            },
        )
        return updated

    async def resolve_event(
        self,
        *,
        organization_id: UUID | str,
        event_id: str,
        actor: str,
        actor_role: str,
        note: str = "",
        auto: bool = False,
    ) -> AlertEvent:
        existing = await self._events.get(event_id)
        if existing is None or existing.organization_id != str(organization_id):
            raise AlertEventNotFound(f"alert event not found: {event_id}")
        updated = await self._events.resolve(event_id, note=note)
        if updated is None:
            return existing
        await self._audit.emit(
            organization_id=organization_id,
            actor=AuditActor(
                actor_id=actor or "system",
                actor_type=AuditActorType.SYSTEM if auto else AuditActorType.HUMAN,
                role=actor_role if not auto else "system",
            ),
            action=(
                AuditAction.ALERT_AUTO_RESOLVED if auto else AuditAction.ALERT_RESOLVED
            ),
            target=AuditTarget(
                target_type=AuditTargetType.ALERT_EVENT,
                target_id=updated.id,
                display=updated.rule_name,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="alert.resolve"),
            metadata={
                "event_id": updated.id,
                "rule_id": updated.rule_id,
                "rule_name": updated.rule_name,
                "note": note,
                "auto": auto,
            },
        )
        return updated

    # ------------------------------------------------------------------
    # Operator summary
    # ------------------------------------------------------------------
    async def build_operator_summary(
        self,
        *,
        organization_id: UUID | str,
        settings: AppSettings,
        runtime_service: RuntimeReadinessService,
    ) -> OperatorSummary:
        """Combine the launch-gate profile, recent alerts, and rule counts."""

        profile = await runtime_service.build_profile(
            organization_id=organization_id
        )
        backup_age_hours: float | None = None
        if profile.last_backup is not None:
            backup_age_hours = profile.last_backup.age_seconds() / 3600.0
        heartbeat_age_seconds: float | None = (
            profile.worker_heartbeat.age_seconds if profile.worker_heartbeat else None
        )
        recent, _ = await self._events.list_for_org(
            organization_id,
            status=AlertEventStatus.FIRING,
            limit=5,
            offset=0,
        )
        open_by_sev: dict[str, int] = {"info": 0, "warning": 0, "critical": 0}
        for sev in (AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL):
            _, total = await self._events.list_for_org(
                organization_id,
                status=AlertEventStatus.FIRING,
                severity=sev,
                limit=1,
                offset=0,
            )
            open_by_sev[sev.value] = int(total)
        rules = await self._rules.list_for_org(organization_id)
        rules_enabled = sum(1 for r in rules if r.enabled)
        return OperatorSummary(
            environment_mode=profile.mode.value,
            gate_passed=profile.gate.passed,
            gate_blocking=tuple(
                {"name": c.name, "detail": c.detail}
                for c in profile.gate.blocking_checks
            ),
            gate_warnings=tuple(
                {"name": c.name, "detail": c.detail}
                for c in profile.gate.warning_checks
            ),
            backup_freshness=profile.backup_freshness.value,
            backup_age_hours=backup_age_hours,
            worker_heartbeat_age_seconds=heartbeat_age_seconds,
            open_alerts_by_severity=open_by_sev,
            recent_alerts=recent,
            rules_total=len(rules),
            rules_enabled=rules_enabled,
        )


async def list_admin_user_ids(
    session: AsyncSession, organization_id: UUID | str
) -> list[str]:
    """Return the user ids of owner/admin members of an organization.

    Used by the alert evaluator to dispatch in-app and email
    notifications to the operator surface. A real product would
    pull a notification-policy from the user preferences; the
    first slice notifies every owner/admin in the workspace so
    the alert is impossible to miss.
    """

    rows = await session.execute(
        select(OrganizationMembershipRow.user_id).where(
            (OrganizationMembershipRow.organization_id == str(organization_id))
            & (OrganizationMembershipRow.role.in_(("owner", "admin")))
            & (OrganizationMembershipRow.state == "active")
        )
    )
    return [str(uid) for uid in rows.scalars().all()]


__all__ = [
    "AlertEventListView",
    "AlertEventNotFound",
    "AlertRuleListView",
    "AlertRuleNotFound",
    "AlertRuleValidationError",
    "AlertService",
    "OperatorSummary",
    "list_admin_user_ids",
    "sanitize_alert_payload",
]
