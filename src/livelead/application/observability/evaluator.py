"""Alert evaluator (US-041).

Runs the periodic tick that reads the durable signals, applies the
closed operator grammar, and produces or resolves alert events.
The evaluator is read-only with respect to product state: it
persists alert events and dispatches notifications through the
existing `NotificationService` (US-029), but it never pauses
jobs, disables connectors, flips live toggles, or rolls back the
environment.

The evaluator is intentionally synchronous in shape so a worker
can call `await evaluate_all()` from a single tick and the test
suite can drive it with a stubbed signal factory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.notifications.notification_service import NotificationService
from livelead.application.observability.alert_service import (
    AlertService,
    list_admin_user_ids,
)
from livelead.application.observability.signals import (
    SignalProvider,
    SignalProviderFactory,
    SignalSample,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditActor, AuditTarget
from livelead.domain.notifications.models import (
    NotificationCandidate,
    NotificationChannel,
    NotificationType,
    SourceRecordType,
)
from livelead.domain.observability.enums import (
    AlertEventStatus,
    AlertMetric,
    AlertSeverity,
)
from livelead.domain.observability.models import (
    AlertEvent,
    AlertRule,
    evaluate_threshold,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload

logger = logging.getLogger("livelead.observability_evaluator")


@dataclass(frozen=True, slots=True)
class TickOutcome:
    organization_id: str
    rules_evaluated: int
    events_fired: int
    events_suppressed: int
    events_resolved: int
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


class AlertEvaluator:
    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        notification_service: NotificationService | None = None,
        signal_factory: SignalProviderFactory | None = None,
        alert_service: AlertService | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._notifications = notification_service
        self._signal_factory = signal_factory or SignalProviderFactory()
        self._alert_service = alert_service or AlertService(
            session,
            audit_service=self._audit,
            signal_factory=self._signal_factory,
        )

    @property
    def signal_factory(self) -> SignalProviderFactory:
        return self._signal_factory

    @property
    def alert_service(self) -> AlertService:
        return self._alert_service

    async def evaluate_organization(
        self, organization_id: str
    ) -> TickOutcome:
        """Run one tick for a single organization."""

        rules = await self._alert_service.rule_repo.list_enabled()
        rules_for_org = [r for r in rules if r.organization_id == organization_id]
        fired = 0
        suppressed = 0
        resolved = 0
        for rule in rules_for_org:
            outcome = await self._evaluate_rule(rule, organization_id)
            if outcome == "fired":
                fired += 1
            elif outcome == "suppressed":
                suppressed += 1
            elif outcome == "resolved":
                resolved += 1
        return TickOutcome(
            organization_id=organization_id,
            rules_evaluated=len(rules_for_org),
            events_fired=fired,
            events_suppressed=suppressed,
            events_resolved=resolved,
        )

    async def evaluate_all_organizations(self) -> list[TickOutcome]:
        """Run one tick for every organization that has enabled rules."""

        all_rules = await self._alert_service.rule_repo.list_enabled()
        org_ids = sorted({r.organization_id for r in all_rules})
        outcomes: list[TickOutcome] = []
        for org_id in org_ids:
            outcomes.append(await self.evaluate_organization(org_id))
        return outcomes

    async def _evaluate_rule(
        self, rule: AlertRule, organization_id: str
    ) -> str:
        provider: SignalProvider | None = self._signal_factory.get(
            rule.metric.value
        )
        if provider is None:
            logger.warning(
                "alert_evaluator_no_provider rule_id=%s metric=%s",
                rule.id,
                rule.metric.value,
            )
            return "skipped"
        sample = await provider.read(
            self._session,
            organization_id=organization_id,
            window_seconds=rule.window_seconds,
        )
        # `inf` means "no signal yet" (e.g. no backup snapshot). The
        # seed rule for stale backup expects `inf` to fire on the
        # very first tick. `evaluate_threshold` returns True for
        # `inf > threshold` which is what we want.
        fires = evaluate_threshold(rule.operator, sample.value, rule.threshold)
        fired_at = datetime.utcnow()
        dedup_key = rule.dedup_bucket(fired_at)
        open_event = await self._alert_service.event_repo.get_open_for_dedup(dedup_key)
        if fires:
            if open_event is not None:
                # Cooldown is in effect; record a suppressed row so the
                # operator can see how many duplicate firings the
                # rule generated.
                await self._record_suppressed(
                    rule=rule,
                    organization_id=organization_id,
                    dedup_key=dedup_key,
                    sample=sample,
                    fired_at=fired_at,
                )
                return "suppressed"
            payload, _ = sanitize_alert_payload(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "metric": rule.metric.value,
                    "operator": rule.operator.value,
                    "threshold": rule.threshold,
                    "value": sample.value,
                    "window_seconds": sample.window_seconds,
                    "details": sample.details or {},
                }
            )
            event = await self._alert_service.event_repo.add(
                organization_id=organization_id,
                rule_id=rule.id,
                rule_name=rule.name,
                metric=rule.metric,
                severity=rule.severity,
                payload=payload,
                dedup_key=dedup_key,
                correlation_id="",
                status=AlertEventStatus.FIRING,
                fired_at=fired_at,
            )
            await self._audit_emit(
                organization_id=organization_id,
                action=AuditAction.ALERT_FIRED,
                event=event,
                rule=rule,
                actor=AuditActor(
                    actor_id="system",
                    actor_type=AuditActorType.SYSTEM,
                    role="system",
                ),
            )
            await self._dispatch_notification(event, rule)
            return "fired"
        # No longer firing: resolve any open event for this rule, regardless
        # of the cooldown bucket. The dedup bucket can roll over while a
        # signal is still failing; the resolution path must scan by rule id
        # so a long-running outage eventually clears the operator's inbox.
        if not fires:
            open_event = await self._alert_service.event_repo.get_open_for_rule(
                organization_id, rule.id
            )
            if open_event is not None:
                await self._alert_service.resolve_event(
                    organization_id=organization_id,
                    event_id=open_event.id,
                    actor="system",
                    actor_role="system",
                    note="auto-resolved: signal cleared",
                    auto=True,
                )
                return "resolved"
            return "ok"

    async def _record_suppressed(
        self,
        *,
        rule: AlertRule,
        organization_id: str,
        dedup_key: str,
        sample: SignalSample,
        fired_at: datetime,
    ) -> AlertEvent:
        payload, _ = sanitize_alert_payload(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "metric": rule.metric.value,
                "threshold": rule.threshold,
                "value": sample.value,
                "details": sample.details or {},
                "suppressed": True,
            }
        )
        event = await self._alert_service.event_repo.add(
            organization_id=organization_id,
            rule_id=rule.id,
            rule_name=rule.name,
            metric=rule.metric,
            severity=rule.severity,
            payload=payload,
            dedup_key=dedup_key,
            status=AlertEventStatus.SUPPRESSED,
            fired_at=fired_at,
        )
        return event

    async def _dispatch_notification(
        self, event: AlertEvent, rule: AlertRule
    ) -> None:
        if self._notifications is None:
            return
        org_id = event.organization_id
        user_ids = await list_admin_user_ids(self._session, org_id)
        if not user_ids:
            logger.info(
                "alert_dispatch_no_admins org_id=%s event_id=%s", org_id, event.id
            )
            return
        # Build the title / summary once; each user receives their
        # own candidate so the in-app inbox and email channel use
        # the per-user preference matrix from US-029.
        title = f"Alert: {rule.name}"
        summary = (
            f"Metric {rule.metric.value} {rule.operator.value} "
            f"{rule.threshold} (observed {event.payload.get('value', '?')})"
        )
        deep_link = f"/admin/observability?event={event.id}"
        for user_id in user_ids:
            try:
                await self._notifications.deliver_candidate(
                    request=None,
                    candidate=NotificationCandidate(
                        organization_id=org_id if False else _org_uuid(org_id),
                        user_id=_user_uuid(user_id),
                        notification_type=NotificationType.ALERT_FIRED,
                        source_record_type=SourceRecordType.ALERT_EVENT,
                        source_record_id=str(event.id),
                        title=title,
                        summary=summary,
                        deep_link=deep_link,
                    ),
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "alert_dispatch_failed event_id=%s user_id=%s err=%s",
                    event.id,
                    user_id,
                    exc,
                )

    async def _audit_emit(
        self,
        *,
        organization_id: str,
        action: AuditAction,
        event: AlertEvent,
        rule: AlertRule,
        actor: AuditActor,
    ) -> None:
        await self._audit.emit(
            organization_id=organization_id,
            actor=actor,
            action=action,
            target=AuditTarget(
                target_type=AuditTargetType.ALERT_EVENT,
                target_id=event.id,
                display=rule.name,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="alert.evaluator"),
            metadata={
                "event_id": event.id,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "metric": rule.metric.value,
                "severity": event.severity.value,
                "dedup_key": event.dedup_key,
            },
        )


def _org_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except (TypeError, ValueError):
        return UUID("00000000-0000-4000-8000-000000000001")


def _user_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except (TypeError, ValueError):
        return UUID("00000000-0000-4000-8000-000000000002")


def new_correlation_id() -> str:
    return uuid4().hex[:32]


__all__ = [
    "AlertEvaluator",
    "TickOutcome",
    "new_correlation_id",
]
