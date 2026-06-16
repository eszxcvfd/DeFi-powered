"""Alert evaluator worker tasks (US-041).

Periodic actor that runs the alert evaluator tick. The actor is
driven by either an explicit enqueue (e.g. by the scheduler after
a key product path completes) or by a periodic scheduler tick.
The actor always uses the worker's session factory so the
evaluator can persist alert events and dispatch notifications
through the existing infrastructure.
"""

from __future__ import annotations

import asyncio
import json
import logging

import dramatiq

from livelead.application.audit.audit_service import AuditService
from livelead.application.notifications.notification_service import (
    NotificationService,
)
from livelead.application.observability import AlertEvaluator, AlertService
from livelead.infrastructure.db.session import create_engine, create_session_factory
from livelead.infrastructure.observability.worker_heartbeat import (
    record_heartbeat_async,
)
from livelead.infrastructure.queue.broker import configure_broker
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.observability_worker")

_settings = parse_settings()
configure_broker(_settings)
_engine = create_engine(_settings)
_session_factory = create_session_factory(_engine)


async def _run_evaluator(organization_id: str | None) -> dict:
    async with _session_factory() as session:
        audit = AuditService(session)
        notifications = NotificationService(session, audit_service=audit)
        alert_service = AlertService(session, audit_service=audit)
        evaluator = AlertEvaluator(
            session,
            audit_service=audit,
            notification_service=notifications,
            alert_service=alert_service,
        )
        if organization_id:
            outcome = await evaluator.evaluate_organization(organization_id)
            outcomes = [outcome]
        else:
            outcomes = await evaluator.evaluate_all_organizations()
        await session.commit()
        return {
            "outcome": "completed",
            "ticks": [
                {
                    "organization_id": o.organization_id,
                    "rules_evaluated": o.rules_evaluated,
                    "events_fired": o.events_fired,
                    "events_suppressed": o.events_suppressed,
                    "events_resolved": o.events_resolved,
                    "evaluated_at": o.evaluated_at.isoformat(),
                }
                for o in outcomes
            ],
        }


@dramatiq.actor(queue_name="default", max_retries=0)
def run_alert_evaluator(organization_id: str | None = None) -> str:
    """Run one evaluator tick. Returns a JSON-serialisable summary.

    `organization_id=None` means "evaluate every organization with
    enabled rules"; the scheduler typically calls it that way. A
    product path can enqueue a per-organization tick for a more
    immediate alert.
    """

    try:
        summary = asyncio.run(_run_evaluator(organization_id))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("alert_evaluator_run_failed: %s", exc)
        return json.dumps({"outcome": "failed", "error": str(exc)})
    try:
        asyncio.run(
            record_heartbeat_async(
                _session_factory,
                last_task="run_alert_evaluator",
                detail=str(organization_id or "all"),
            )
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("alert_evaluator_heartbeat_failed: %s", exc)
    return json.dumps(summary)
