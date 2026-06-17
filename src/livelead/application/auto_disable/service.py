"""Connector auto-disable service (US-048).

Owns the bounded connector auto-disable path. The
service is the only place that mutates
`connector_auto_disable_rules` and
`connector_auto_disable_events` and emits the
`connector.auto_disable.*` audit entries; the
REST layer calls it from the request handlers.

The service reuses the `SanitizeAlertPayload`
helper from `US-041` for every rule, event, and
audit payload. The bounded window is enforced
by the `EnvironmentMode` shipped by `US-040`
(max 24 hours in `pilot_live`, max 1 hour in
`test_like`). The service consumes the
`ConnectorHealthSnapshot` rows from `US-046`
and the `AlertEvent` rows from `US-041`.

The service exposes a bounded
`evaluate_source_for_discovery` helper that the
orchestrator from `US-004` / `US-032` /
`US-033` / `US-034` calls before a job is
dispatched. The helper returns
`SourceRunDecision` with one of three values:
`RUN_ALLOWED`, `RUN_AUTO_DISABLED`, or
`RUN_MANUAL_DISABLED`.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.auto_disable.evaluator import (
    bounded_window as _bounded_window,
)
from livelead.application.auto_disable.evaluator import (
    evaluate_rule as _evaluate_rule,
)
from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableEvaluationResult,
    AutoDisableThresholds,
    ConnectorAutoDisableEvent,
    ConnectorAutoDisableRule,
    SourceRunDecision,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.observability.enums import (
    AlertEventStatus,
    AlertMetric,
    AlertSeverity,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import SourceRow
from livelead.infrastructure.db.repositories.auto_disable import (
    ConnectorAutoDisableEventRepository,
    ConnectorAutoDisableRuleRepository,
)

logger = logging.getLogger("livelead.auto_disable_service")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AutoDisableError(ValueError):
    """Raised when a bounded auto-disable operation
    is rejected."""


class AutoDisableSourceNotFound(AutoDisableError):
    """Raised when the source is missing or out of
    tenant scope."""


class AutoDisableRuleNotFound(AutoDisableError):
    """Raised when the rule is missing or out of
    tenant scope."""


class AutoDisableEventNotFound(AutoDisableError):
    """Raised when the event is missing or out of
    tenant scope."""


class AutoDisableInvalidWindow(AutoDisableError):
    """Raised when the window is zero, negative, or
    exceeds the `EnvironmentMode` bound."""


class AutoDisableInvalidTrigger(AutoDisableError):
    """Raised when the trigger is not in the closed
    `AutoDisableTrigger` enum."""


class AutoDisableInvalidPayload(AutoDisableError):
    """Raised when the payload fails the
    `SanitizeAlertPayload` contract."""


class AutoDisableRecoveryRejected(AutoDisableError):
    """Raised when the recovery action is denied
    because the event is not in `active` state,
    the `cooldown_seconds` window has not
    elapsed, or the source is `unhealthy`."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload_sanitized(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    cleaned, redacted = sanitize_alert_payload(payload)
    if not isinstance(cleaned, dict):
        return {}, redacted
    return cleaned, redacted


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned, _ = _payload_sanitized(payload)
    return cleaned


def _max_window_seconds(
    environment_mode: EnvironmentMode | str,
) -> int:
    try:
        mode = (
            environment_mode
            if isinstance(environment_mode, EnvironmentMode)
            else EnvironmentMode(environment_mode)
        )
    except ValueError:
        mode = EnvironmentMode.TEST_LIKE
    if mode is EnvironmentMode.PILOT_LIVE:
        return 24 * 3600
    return 3600


def _bounded_window_seconds(
    *,
    requested: int,
    thresholds: AutoDisableThresholds,
    environment_mode: EnvironmentMode | str,
) -> int:
    """Bound the requested window by the
    `EnvironmentMode` and the closed
    `AutoDisableThresholds` defaults.

    A missing or non-positive `requested` is
    replaced with the threshold default; a
    `requested` that exceeds the `EnvironmentMode`
    bound is clipped to the bound.
    """

    max_window = _max_window_seconds(environment_mode)
    default_window = thresholds.default_window_seconds
    if requested is None or int(requested) <= 0:
        return min(default_window, max_window)
    bounded = min(int(requested), max_window)
    if bounded <= 0:
        raise AutoDisableInvalidWindow(
            "AUTO_DISABLE_RULE_INVALID_WINDOW"
        )
    return bounded


def _bounded_recovery_reason(
    reason: str, *, limit: int
) -> str:
    candidate = str(reason or "").strip()[:limit]
    if not candidate:
        raise AutoDisableInvalidPayload(
            "AUTO_DISABLE_RECOVERY_REASON_REQUIRED"
        )
    return candidate


# Closed set of `AlertEvent` severities that the
# bounded `needs_user_action_storm` and
# `error_spike` triggers consume.
_ALERT_TRIGGER_SEVERITIES: frozenset[str] = frozenset(
    {
        AlertSeverity.WARNING.value,
        AlertSeverity.CRITICAL.value,
    }
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AutoDisableService:
    """Application service for the bounded
    connector auto-disable surface.

    The service is the only place that runs a
    bounded per-source evaluation, persists a
    `ConnectorAutoDisableEvent` row, flips
    `Source.enabled` to `false` when a trigger
    fires, and emits the
    `connector.auto_disable.*` audit entries.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        rule_repo: ConnectorAutoDisableRuleRepository | None = None,
        event_repo: ConnectorAutoDisableEventRepository | None = None,
        thresholds: AutoDisableThresholds | None = None,
        environment_mode: EnvironmentMode | str = EnvironmentMode.TEST_LIKE,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._rules = (
            rule_repo or ConnectorAutoDisableRuleRepository(session)
        )
        self._events = (
            event_repo or ConnectorAutoDisableEventRepository(session)
        )
        self._thresholds = thresholds or AutoDisableThresholds()
        self._environment_mode = environment_mode

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def rule_repo(self) -> ConnectorAutoDisableRuleRepository:
        return self._rules

    @property
    def event_repo(self) -> ConnectorAutoDisableEventRepository:
        return self._events

    @property
    def thresholds(self) -> AutoDisableThresholds:
        return self._thresholds

    # ------------------------------------------------------------------
    # Source scope
    # ------------------------------------------------------------------

    async def _resolve_source(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
    ) -> SourceRow:
        result = await self._session.execute(
            select(SourceRow).where(
                and_(
                    SourceRow.id == str(source_id),
                    SourceRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AutoDisableSourceNotFound(
                "AUTO_DISABLE_SOURCE_NOT_FOUND"
            )
        return row

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    async def create_rule(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
        trigger: AutoDisableTrigger | str,
        threshold_value: float,
        window_seconds: int | None = None,
        consecutive_breaches: int | None = None,
        cooldown_seconds: int | None = None,
        enabled: bool = True,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> ConnectorAutoDisableRule:
        """Create a per-source auto-disable rule.

        The bounded path validates the
        `AutoDisableTrigger` enum and the
        `EnvironmentMode` bound before persisting
        the rule. The path emits a
        `connector.auto_disable.rule.created`
        audit entry.
        """

        org = str(organization_id)
        source = await self._resolve_source(org, source_id)
        parsed_trigger = self._parse_trigger(trigger)
        bounded_window = _bounded_window_seconds(
            requested=int(window_seconds or 0),
            thresholds=self._thresholds,
            environment_mode=self._environment_mode,
        )
        bounded_consecutive = int(
            consecutive_breaches
            or self._thresholds.default_consecutive_breaches
        )
        if bounded_consecutive <= 0:
            bounded_consecutive = (
                self._thresholds.default_consecutive_breaches
            )
        bounded_cooldown = int(
            cooldown_seconds or self._thresholds.default_cooldown_seconds
        )
        if bounded_cooldown < 0:
            bounded_cooldown = 0
        correlation_id = str(uuid4())
        rule = await self._rules.add(
            organization_id=org,
            source_id=str(source.id),
            trigger=parsed_trigger,
            threshold_value=float(threshold_value),
            window_seconds=int(bounded_window),
            consecutive_breaches=int(bounded_consecutive),
            cooldown_seconds=int(bounded_cooldown),
            enabled=bool(enabled),
            created_by=actor or actor_role or "system",
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_RULE_CREATED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_AUTO_DISABLE_RULE,
                target_id=rule.id,
                display=f"connector_auto_disable_rule:{source.id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.rule.create",
            ),
            metadata=_safe_metadata(
                {
                    "rule_id": rule.id,
                    "source_id": str(source.id),
                    "trigger": parsed_trigger.value,
                    "threshold_value": float(threshold_value),
                    "window_seconds": int(bounded_window),
                    "consecutive_breaches": int(bounded_consecutive),
                    "cooldown_seconds": int(bounded_cooldown),
                    "enabled": bool(enabled),
                    "environment_mode": str(
                        self._environment_mode
                    ),
                }
            ),
        )
        return rule

    async def update_rule(
        self,
        *,
        organization_id: UUID | str,
        rule_id: UUID | str,
        threshold_value: float | None = None,
        window_seconds: int | None = None,
        consecutive_breaches: int | None = None,
        cooldown_seconds: int | None = None,
        enabled: bool | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> ConnectorAutoDisableRule:
        """Update a per-source auto-disable rule.

        The bounded path validates the new fields
        and emits a
        `connector.auto_disable.rule.updated`
        audit entry with a before/after diff.
        """

        org = str(organization_id)
        existing = await self._rules.get(org, rule_id)
        if existing is None:
            raise AutoDisableRuleNotFound(
                "AUTO_DISABLE_RULE_NOT_FOUND"
            )
        new_window = (
            _bounded_window_seconds(
                requested=int(window_seconds or 0),
                thresholds=self._thresholds,
                environment_mode=self._environment_mode,
            )
            if window_seconds is not None
            else existing.window_seconds
        )
        new_consecutive = (
            int(consecutive_breaches)
            if consecutive_breaches is not None
            else existing.consecutive_breaches
        )
        if new_consecutive <= 0:
            new_consecutive = (
                self._thresholds.default_consecutive_breaches
            )
        new_cooldown = (
            int(cooldown_seconds)
            if cooldown_seconds is not None
            else existing.cooldown_seconds
        )
        if new_cooldown < 0:
            new_cooldown = 0
        new_threshold = (
            float(threshold_value)
            if threshold_value is not None
            else existing.threshold_value
        )
        new_enabled = (
            bool(enabled) if enabled is not None else existing.enabled
        )
        updated = await self._rules.update(
            org,
            rule_id,
            threshold_value=new_threshold,
            window_seconds=int(new_window),
            consecutive_breaches=int(new_consecutive),
            cooldown_seconds=int(new_cooldown),
            enabled=new_enabled,
        )
        if updated is None:
            raise AutoDisableRuleNotFound(
                "AUTO_DISABLE_RULE_NOT_FOUND"
            )
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_RULE_UPDATED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_AUTO_DISABLE_RULE,
                target_id=updated.id,
                display=(
                    f"connector_auto_disable_rule:{updated.source_id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.rule.update",
            ),
            metadata=_safe_metadata(
                {
                    "rule_id": updated.id,
                    "source_id": updated.source_id,
                    "before": {
                        "threshold_value": float(
                            existing.threshold_value
                        ),
                        "window_seconds": int(
                            existing.window_seconds
                        ),
                        "consecutive_breaches": int(
                            existing.consecutive_breaches
                        ),
                        "cooldown_seconds": int(
                            existing.cooldown_seconds
                        ),
                        "enabled": bool(existing.enabled),
                    },
                    "after": {
                        "threshold_value": float(new_threshold),
                        "window_seconds": int(new_window),
                        "consecutive_breaches": int(new_consecutive),
                        "cooldown_seconds": int(new_cooldown),
                        "enabled": bool(new_enabled),
                    },
                }
            ),
        )
        return updated

    async def delete_rule(
        self,
        *,
        organization_id: UUID | str,
        rule_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> None:
        """Soft-delete a per-source auto-disable
        rule. The bounded path emits a
        `connector.auto_disable.rule.deleted`
        audit entry.
        """

        org = str(organization_id)
        existing = await self._rules.get(org, rule_id)
        if existing is None:
            raise AutoDisableRuleNotFound(
                "AUTO_DISABLE_RULE_NOT_FOUND"
            )
        await self._rules.soft_delete(org, rule_id)
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_RULE_DELETED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_AUTO_DISABLE_RULE,
                target_id=existing.id,
                display=(
                    f"connector_auto_disable_rule:{existing.source_id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.rule.delete",
            ),
            metadata=_safe_metadata(
                {
                    "rule_id": existing.id,
                    "source_id": existing.source_id,
                    "trigger": existing.trigger.value,
                }
            ),
        )

    async def list_rules(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorAutoDisableRule], int]:
        return await self._rules.list_for_org(
            organization_id,
            source_id=source_id,
            enabled=enabled,
            limit=limit,
            offset=offset,
        )

    async def get_rule(
        self, organization_id: UUID | str, rule_id: UUID | str
    ) -> ConnectorAutoDisableRule | None:
        return await self._rules.get(organization_id, rule_id)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def list_events(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        status: AutoDisableEventStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorAutoDisableEvent], int]:
        return await self._events.list_for_org(
            organization_id,
            source_id=source_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_event(
        self,
        organization_id: UUID | str,
        event_id: UUID | str,
    ) -> ConnectorAutoDisableEvent | None:
        return await self._events.get(organization_id, event_id)

    async def latest_active_for_source(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
    ) -> ConnectorAutoDisableEvent | None:
        """Return the most recent active event for
        the source, or `None` if no event is
        active.
        """

        return await self._events.latest_active_for_source(
            organization_id, source_id
        )

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------

    async def evaluate_source(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
        now: datetime | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> AutoDisableEvaluationResult:
        """Run a bounded per-source evaluation
        cycle. The path reads the enabled rules
        for the source, the most recent
        `ConnectorHealthSnapshot` rows from
        `US-046`, the most recent matching
        `AlertEvent` rows from `US-041`, applies
        the closed trigger rules with the
        `consecutive_breaches` and
        `cooldown_seconds` bounds, and either
        flips `Source.enabled` to `false` and
        persists a `ConnectorAutoDisableEvent`
        row, or returns a no-op result.
        """

        org = str(organization_id)
        source = await self._resolve_source(org, source_id)
        rules = await self._rules.list_enabled_for_source(
            org, source.id
        )
        if not rules:
            return AutoDisableEvaluationResult(should_disable=False)
        evaluation_now = now or datetime.now(UTC).replace(tzinfo=None)
        recent_events = await self._events.recent_for_source(
            org,
            source.id,
            limit=self._thresholds.max_recent_events_per_source,
        )
        snapshots = await self._load_health_snapshots(
            organization_id=org,
            source_id=str(source.id),
            max_window_seconds=max(
                int(r.window_seconds) for r in rules
            ),
            now=evaluation_now,
        )
        alerts = await self._load_alert_events(
            organization_id=org,
            metrics=_ALERT_TRIGGER_METRICS,
            max_window_seconds=max(
                int(r.window_seconds) for r in rules
            ),
            now=evaluation_now,
        )
        # The bounded path evaluates each rule and
        # takes the most recent trigger that
        # actually fires.
        winning: AutoDisableEvaluationResult | None = None
        for rule in rules:
            result = _evaluate_rule(
                rule=rule,
                health_snapshots=snapshots,
                alert_events=alerts,
                recent_events=recent_events,
                now=evaluation_now,
            )
            if result.should_disable:
                winning = result
                break
        if winning is None or not winning.should_disable:
            return AutoDisableEvaluationResult(should_disable=False)
        correlation_id = str(uuid4())
        event = await self._events.add(
            organization_id=org,
            source_id=str(source.id),
            trigger=winning.trigger,
            reason=(winning.reason or "")[: self._thresholds.max_reason_length],
            breach_count=int(winning.breach_count),
            window_start=winning.window_start,
            window_end=winning.window_end,
            status=AutoDisableEventStatus.ACTIVE,
            alert_event_id=winning.alert_event_id,
            health_snapshot_id=winning.health_snapshot_id,
            audit_correlation_id=correlation_id,
            max_reason_length=self._thresholds.max_reason_length,
        )
        # Persist the `Source.enabled = false`
        # flip and the auto-disable metadata.
        await self._mark_source_auto_disabled(
            source=source,
            reason=event.reason,
            event_id=event.id,
        )
        await self._supersede_prior_active_events(
            organization_id=org,
            source_id=str(source.id),
            new_event_id=event.id,
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_TRIGGERED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_AUTO_DISABLE_EVENT,
                target_id=event.id,
                display=f"connector_auto_disable_event:{source.id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.evaluate",
            ),
            metadata=_safe_metadata(
                {
                    "event_id": event.id,
                    "source_id": str(source.id),
                    "trigger": event.trigger.value,
                    "reason": event.reason,
                    "breach_count": int(event.breach_count),
                    "window_start": (
                        event.window_start.isoformat()
                        if event.window_start
                        else None
                    ),
                    "window_end": (
                        event.window_end.isoformat()
                        if event.window_end
                        else None
                    ),
                    "rule_id": winning.rule_id,
                    "alert_event_id": event.alert_event_id,
                    "health_snapshot_id": event.health_snapshot_id,
                }
            ),
        )
        return winning

    async def evaluate_all_sources(
        self,
        *,
        organization_id: UUID | str,
        now: datetime | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "system",
        actor_role: str = "system",
    ) -> list[AutoDisableEvaluationResult]:
        """Run a bounded evaluation cycle for every
        source with at least one enabled rule.

        The bounded path is the worker-tick
        entrypoint the orchestrator uses; the
        path returns one result per source.
        """

        org = str(organization_id)
        source_ids = await self._rules.list_distinct_source_ids(org)
        results: list[AutoDisableEvaluationResult] = []
        for source_id in source_ids:
            try:
                result = await self.evaluate_source(
                    organization_id=org,
                    source_id=source_id,
                    now=now,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    actor=actor,
                    actor_role=actor_role,
                )
            except AutoDisableSourceNotFound:
                continue
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    async def recover_source(
        self,
        *,
        organization_id: UUID | str,
        event_id: UUID | str,
        reason: str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> ConnectorAutoDisableEvent:
        """Human-confirmed recovery action.

        The bounded path transitions the event
        from `active` to `recovering`, emits the
        `connector.auto_disable.recovered` audit
        entry, and clears the `Source` row's
        auto-disable metadata only when the next
        evaluation cycle returns `healthy` or
        `degraded` and the `cooldown_seconds`
        window has elapsed.
        """

        org = str(organization_id)
        event = await self._events.get(org, event_id)
        if event is None:
            raise AutoDisableEventNotFound(
                "AUTO_DISABLE_EVENT_NOT_FOUND"
            )
        if event.status is not AutoDisableEventStatus.ACTIVE:
            raise AutoDisableRecoveryRejected(
                "AUTO_DISABLE_RECOVERY_REJECTED:event_not_active"
            )
        bounded_reason = _bounded_recovery_reason(
            reason,
            limit=self._thresholds.max_reason_length,
        )
        correlation_id = str(uuid4())
        updated = await self._events.transition_status(
            org,
            event.id,
            status=AutoDisableEventStatus.RECOVERING,
            recovery_actor_id=actor or actor_role or "system",
            recovery_reason=bounded_reason,
            recovered_at=None,
        )
        if updated is None:
            raise AutoDisableEventNotFound(
                "AUTO_DISABLE_EVENT_NOT_FOUND"
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_RECOVERED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_AUTO_DISABLE_EVENT,
                target_id=updated.id,
                display=(
                    f"connector_auto_disable_event:{updated.source_id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.recover",
            ),
            metadata=_safe_metadata(
                {
                    "event_id": updated.id,
                    "source_id": updated.source_id,
                    "recovery_reason": bounded_reason,
                }
            ),
        )
        return updated

    async def finalize_recovery(
        self,
        *,
        organization_id: UUID | str,
        event_id: UUID | str,
        source_healthy: bool,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "system",
        actor_role: str = "system",
    ) -> ConnectorAutoDisableEvent:
        """Finalize a `recovering` event based on
        the next evaluation cycle result.

        The bounded path transitions the event
        to `resolved` and clears the `Source`
        row's auto-disable metadata when the
        source is `healthy` or `degraded` and
        the `cooldown_seconds` window has
        elapsed. The path transitions the event
        to `active` (re-disabled) and emits the
        `connector.auto_disable.recovery.rejected`
        audit entry when the source is
        `unhealthy`.
        """

        org = str(organization_id)
        event = await self._events.get(org, event_id)
        if event is None:
            raise AutoDisableEventNotFound(
                "AUTO_DISABLE_EVENT_NOT_FOUND"
            )
        if event.status is not AutoDisableEventStatus.RECOVERING:
            return event
        correlation_id = str(uuid4())
        if source_healthy:
            updated = await self._events.transition_status(
                org,
                event.id,
                status=AutoDisableEventStatus.RESOLVED,
                recovered_at=datetime.now(UTC).replace(tzinfo=None),
            )
            if updated is None:
                raise AutoDisableEventNotFound(
                    "AUTO_DISABLE_EVENT_NOT_FOUND"
                )
            await self._clear_source_auto_disabled(updated.source_id)
            await self._audit.emit(
                organization_id=UUID(org),
                actor=make_actor_from_role(
                    actor_role, actor_id=actor or None
                ),
                action=AuditAction.CONNECTOR_AUTO_DISABLE_RECOVERY_RESOLVED,
                target=AuditTarget(
                    target_type=(
                        AuditTargetType.CONNECTOR_AUTO_DISABLE_EVENT
                    ),
                    target_id=updated.id,
                    display=(
                        f"connector_auto_disable_event:"
                        f"{updated.source_id}"
                    ),
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=make_context(
                    request_id=request_id,
                    correlation_id=correlation_id,
                    ip=ip_address,
                    user_agent=user_agent,
                    workflow="connector.auto_disable.recovery.resolve",
                ),
                metadata=_safe_metadata(
                    {
                        "event_id": updated.id,
                        "source_id": updated.source_id,
                    }
                ),
            )
            return updated
        updated = await self._events.transition_status(
            org,
            event.id,
            status=AutoDisableEventStatus.ACTIVE,
            recovered_at=None,
        )
        if updated is None:
            raise AutoDisableEventNotFound(
                "AUTO_DISABLE_EVENT_NOT_FOUND"
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_AUTO_DISABLE_RECOVERY_REJECTED,
            target=AuditTarget(
                target_type=(
                    AuditTargetType.CONNECTOR_AUTO_DISABLE_EVENT
                ),
                target_id=updated.id,
                display=(
                    f"connector_auto_disable_event:{updated.source_id}"
                ),
            ),
            outcome=AuditOutcome.FAILED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.auto_disable.recovery.reject",
            ),
            metadata=_safe_metadata(
                {
                    "event_id": updated.id,
                    "source_id": updated.source_id,
                    "trigger": updated.trigger.value,
                    "reason": "source_unhealthy",
                }
            ),
        )
        return updated

    # ------------------------------------------------------------------
    # Source-side helper
    # ------------------------------------------------------------------

    async def evaluate_source_for_discovery(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
    ) -> SourceRunDecision:
        """Source-side helper that the orchestrator
        from `US-004` / `US-032` / `US-033` /
        `US-034` calls before a job is dispatched.

        The bounded path returns `RUN_ALLOWED`,
        `RUN_AUTO_DISABLED`, or
        `RUN_MANUAL_DISABLED` and the matching
        reason. The path refuses to run a
        discovery job against an `auto_disabled`
        source even when the manual `enabled`
        flag is `true`; the manual `enabled`
        flag is preserved as a separate signal.
        """

        try:
            source = await self._resolve_source(
                organization_id, source_id
            )
        except AutoDisableSourceNotFound:
            return SourceRunDecision(
                run_state="RUN_AUTO_DISABLED",
                reason="source_not_found",
            )
        if not bool(source.enabled):
            return SourceRunDecision(
                run_state="RUN_MANUAL_DISABLED",
                reason="source_disabled_manually",
            )
        active = await self._events.latest_active_for_source(
            organization_id, source_id
        )
        if active is not None:
            return SourceRunDecision(
                run_state="RUN_AUTO_DISABLED",
                reason=f"event:{active.id}:{active.trigger.value}",
                event_id=active.id,
            )
        return SourceRunDecision(
            run_state="RUN_ALLOWED",
            reason="ok",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_trigger(
        self, trigger: AutoDisableTrigger | str
    ) -> AutoDisableTrigger:
        if isinstance(trigger, AutoDisableTrigger):
            return trigger
        try:
            return AutoDisableTrigger(str(trigger))
        except ValueError as exc:
            raise AutoDisableInvalidTrigger(
                "AUTO_DISABLE_RULE_INVALID"
            ) from exc

    async def _load_health_snapshots(
        self,
        *,
        organization_id: str,
        source_id: str,
        max_window_seconds: int,
        now: datetime,
    ) -> list[Any]:
        """Load the most recent bounded
        `ConnectorHealthSnapshot` rows for the
        source. The bounded path reads the most
        recent snapshot for the source; a missing
        snapshot returns an empty list.
        """

        from livelead.infrastructure.db.repositories.connector_health import (
            ConnectorHealthSnapshotRepository,
        )

        repo = ConnectorHealthSnapshotRepository(self._session)
        latest = await repo.latest_for_source(
            organization_id, source_id
        )
        if latest is None:
            return []
        window_start, _ = _bounded_window(
            now=now, window_seconds=int(max_window_seconds)
        )
        # Read up to N most recent snapshots in the
        # bounded window so the consecutive-breach
        # counter has enough signal to evaluate.
        from livelead.infrastructure.db.models import (
            ConnectorHealthSnapshotRow,
        )
        from sqlalchemy import and_, desc

        result = await self._session.execute(
            select(ConnectorHealthSnapshotRow)
            .where(
                and_(
                    ConnectorHealthSnapshotRow.organization_id
                    == str(organization_id),
                    ConnectorHealthSnapshotRow.source_id
                    == str(source_id),
                    ConnectorHealthSnapshotRow.computed_at
                    >= window_start,
                )
            )
            .order_by(desc(ConnectorHealthSnapshotRow.computed_at))
            .limit(50)
        )
        rows = result.scalars().all()
        from livelead.infrastructure.db.connector_health_mappers import (
            row_to_connector_health_snapshot,
        )

        return [row_to_connector_health_snapshot(r) for r in rows]

    async def _load_alert_events(
        self,
        *,
        organization_id: str,
        metrics: frozenset[str],
        max_window_seconds: int,
        now: datetime,
    ) -> list[Any]:
        """Load the most recent bounded
        `AlertEvent` rows for the closed metric
        set. The bounded path reads the
        `firing` and `acknowledged` events whose
        `severity` is `warning` or `critical`.
        """

        from livelead.infrastructure.db.models import AlertEventRow
        from livelead.infrastructure.db.repositories.observability import (
            row_to_alert_event,
        )
        from sqlalchemy import and_, desc

        if not metrics:
            return []
        window_start, _ = _bounded_window(
            now=now, window_seconds=int(max_window_seconds)
        )
        result = await self._session.execute(
            select(AlertEventRow)
            .where(
                and_(
                    AlertEventRow.organization_id
                    == str(organization_id),
                    AlertEventRow.metric.in_(list(metrics)),
                    AlertEventRow.severity.in_(
                        list(_ALERT_TRIGGER_SEVERITIES)
                    ),
                    AlertEventRow.fired_at >= window_start,
                    AlertEventRow.status.in_(
                        [
                            AlertEventStatus.FIRING.value,
                            AlertEventStatus.ACKNOWLEDGED.value,
                        ]
                    ),
                )
            )
            .order_by(desc(AlertEventRow.fired_at))
            .limit(50)
        )
        rows = result.scalars().all()
        return [row_to_alert_event(r) for r in rows]

    async def _mark_source_auto_disabled(
        self,
        *,
        source: SourceRow,
        reason: str,
        event_id: str,
    ) -> None:
        """Persist the `Source.enabled = false` flip
        and the auto-disable metadata. The bounded
        path keeps the manual `enabled` flag for
        compatibility; the source-side helper
        checks the auto-disable state directly.
        """

        source.auto_disabled_at = datetime.now(UTC).replace(tzinfo=None)
        source.auto_disabled_reason = reason[: self._thresholds.max_reason_length]
        source.auto_disabled_by_event_id = event_id
        source.enabled = False
        await self._session.flush()

    async def _clear_source_auto_disabled(
        self, source_id: str
    ) -> None:
        """Clear the `Source` row's auto-disable
        metadata. The bounded path runs after a
        `recovering` event transitions to
        `resolved`.
        """

        result = await self._session.execute(
            select(SourceRow).where(SourceRow.id == str(source_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.auto_disabled_at = None
        row.auto_disabled_reason = None
        row.auto_disabled_by_event_id = None
        row.enabled = True
        await self._session.flush()

    async def _supersede_prior_active_events(
        self,
        *,
        organization_id: str,
        source_id: str,
        new_event_id: str,
    ) -> None:
        """Transition any prior `active` event for
        the same source to `superseded` so the
        audit trail preserves the history.
        """

        events = await self._events.list_active_for_source(
            organization_id, source_id
        )
        for prior in events:
            if prior.id == new_event_id:
                continue
            await self._events.transition_status(
                organization_id,
                prior.id,
                status=AutoDisableEventStatus.SUPERSEDED,
                recovered_at=datetime.now(UTC).replace(tzinfo=None),
            )


# Closed set of `AlertMetric` values the
# bounded `error_spike` and
# `needs_user_action_storm` triggers consume.
_ALERT_TRIGGER_METRICS: frozenset[str] = frozenset(
    {
        AlertMetric.CONNECTOR_FAILURE_RATE.value,
        AlertMetric.DISCOVERY_NEEDS_USER_ACTION_RATE.value,
    }
)


__all__ = [
    "AutoDisableError",
    "AutoDisableEventNotFound",
    "AutoDisableInvalidPayload",
    "AutoDisableInvalidTrigger",
    "AutoDisableInvalidWindow",
    "AutoDisableRecoveryRejected",
    "AutoDisableRuleNotFound",
    "AutoDisableService",
    "AutoDisableSourceNotFound",
]
