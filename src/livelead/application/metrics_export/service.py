"""Metrics export policy service (US-042).

Owns the policy CRUD, the acceptance gate, the test export
endpoint, and the audit trail. The service is intentionally
synchronous in shape: the REST handlers run it from request
handlers and the worker tick runs it from a periodic actor.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime
from secrets import compare_digest
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.metrics_export.exporter import (
    DefaultTransportFactory,
    MetricsExporter,
    TransportFactory,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.metrics_export.enums import (
    ExportStatus,
    MetricsSink,
    OtelProtocol,
    SUPPORTED_OTEL_PROTOCOLS,
    SUPPORTED_SINKS,
)
from livelead.domain.metrics_export.models import (
    ExportResult,
    MetricsExportPolicy,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
    validate_policy_payload,
)
from livelead.infrastructure.db.repositories.metrics_export import (
    MetricsExportPolicyRepository,
)

logger = logging.getLogger("livelead.metrics_export_service")


class ExportPolicyValidationError(ValueError):
    """Raised when the policy payload fails the closed grammar."""


class ExportPolicyAcceptanceRequired(Exception):
    """Raised when a sink is enabled without `accepted_by` / `accepted_at`."""


def _hash_scrape_token(token: str) -> str:
    """Hash a Prometheus scrape token with SHA-256.

    The application uses a salted SHA-256 hash because the
    scrape token is a low-entropy secret that the exporter
    needs to verify on every scrape. A future story can swap
    the SHA-256 for argon2id if the secret is shared with
    another service; the contract is "compare a presented
    token against the stored hash".
    """

    salt = os.environ.get("LIVELEAD_PROMETHEUS_SCRAPE_SALT", "livelead-default-salt")
    h = hmac.new(salt.encode("utf-8"), token.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def verify_scrape_token(token: str, stored_hash: str) -> bool:
    """Constant-time compare of a presented scrape token against the stored hash."""

    candidate = _hash_scrape_token(token)
    return compare_digest(candidate, stored_hash or "")


class MetricsExportService:
    """Application service for the metrics export policy surface.

    The service is the only writer of `MetricsExportPolicyRow`
    and the only place that enforces the acceptance gate. The
    REST layer wraps it in Pydantic schemas; the worker tick
    runs `MetricsExporter` for the periodic export.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        exporter: MetricsExporter | None = None,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._policy_repo = MetricsExportPolicyRepository(session)
        self._transport_factory = transport_factory or DefaultTransportFactory()
        self._exporter = exporter or MetricsExporter(
            session=session,
            transport_factory=self._transport_factory,
            audit_service=self._audit,
        )

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def policy_repo(self) -> MetricsExportPolicyRepository:
        return self._policy_repo

    @property
    def exporter(self) -> MetricsExporter:
        return self._exporter

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    async def get_policy(self, organization_id: UUID | str) -> MetricsExportPolicy:
        return await self._policy_repo.get_or_default(organization_id)

    async def update_policy(
        self,
        *,
        organization_id: UUID | str,
        actor: str,
        actor_role: str,
        prometheus: PrometheusConfig | None = None,
        otel: OtelConfig | None = None,
        sentry: SentryConfig | None = None,
        scrape_token_plaintext: str | None = None,
        accepted_by: str | None = None,
    ) -> MetricsExportPolicy:
        """Update one or more sinks on the policy and emit an audit entry.

        The service enforces the acceptance gate: a sink cannot
        be enabled without `accepted_by` and `accepted_at`.
        The REST layer is responsible for surfacing the error
        to the operator; the service refuses to persist a
        half-enabled policy.
        """

        org = str(organization_id)
        existing = await self._policy_repo.get_or_default(org)
        new_prom = existing.prometheus
        new_otel = existing.otel
        new_sentry = existing.sentry
        if prometheus is not None:
            new_prom = prometheus
        if otel is not None:
            new_otel = otel
        if sentry is not None:
            new_sentry = sentry
        # Hash the scrape token if a plaintext was provided. The
        # token never reaches the policy row in plaintext.
        if scrape_token_plaintext is not None and prometheus is not None:
            new_prom = PrometheusConfig(
                enabled=new_prom.enabled,
                scrape_token_hash=_hash_scrape_token(scrape_token_plaintext),
                allowed_source_cidrs=new_prom.allowed_source_cidrs,
                retention_note=new_prom.retention_note,
            )
        try:
            validate_policy_payload(
                prometheus=new_prom,
                otel=new_otel,
                sentry=new_sentry,
            )
        except ValueError as exc:
            raise ExportPolicyValidationError(str(exc)) from exc
        # Enforce the acceptance gate for any newly enabled sink.
        # The check accepts a sink enablement when EITHER the
        # request provides a new `accepted_by` (the service will
        # set `accepted_at` to now) OR the existing policy
        # already has an `accepted_at` recorded. This keeps the
        # contract honest: a sink cannot be enabled silently.
        for sink, config in (
            (MetricsSink.PROMETHEUS_EXPOSITION, new_prom),
            (MetricsSink.OTEL_COLLECTOR, new_otel),
            (MetricsSink.SENTRY_INGEST, new_sentry),
        ):
            if config.enabled and not existing.sink_enabled(sink):
                if not accepted_by and not existing.accepted_at:
                    raise ExportPolicyAcceptanceRequired(
                        f"EXPORT_POLICY_ACCEPTANCE_REQUIRED:sink:{sink.value}"
                    )
        new_accepted_by = existing.accepted_by
        new_accepted_at = existing.accepted_at
        if accepted_by is not None:
            new_accepted_by = accepted_by
            new_accepted_at = datetime.utcnow()
        policy = MetricsExportPolicy(
            organization_id=org,
            prometheus=new_prom,
            otel=new_otel,
            sentry=new_sentry,
            prometheus_last_status=existing.prometheus_last_status,
            prometheus_last_export_at=existing.prometheus_last_export_at,
            otel_last_status=existing.otel_last_status,
            otel_last_export_at=existing.otel_last_export_at,
            sentry_last_status=existing.sentry_last_status,
            sentry_last_export_at=existing.sentry_last_export_at,
            accepted_by=new_accepted_by,
            accepted_at=new_accepted_at,
        )
        saved = await self._policy_repo.upsert(organization_id=org, policy=policy)
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.METRICS_EXPORT_POLICY_UPDATED,
            target=AuditTarget(
                target_type=AuditTargetType.METRICS_EXPORT_POLICY,
                target_id=org,
                display="metrics_export_policy",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="metrics.export_policy.update"),
            metadata={
                "prometheus_enabled": new_prom.enabled,
                "otel_enabled": new_otel.enabled,
                "sentry_enabled": new_sentry.enabled,
                "accepted_by": new_accepted_by,
                "accepted_at": (
                    new_accepted_at.isoformat() if new_accepted_at else None
                ),
            },
        )
        return saved

    # ------------------------------------------------------------------
    # Test export
    # ------------------------------------------------------------------

    async def test_policy(
        self,
        *,
        organization_id: UUID | str,
        actor: str,
        actor_role: str,
    ) -> dict[MetricsSink, ExportResult]:
        """Run a single round-trip per enabled sink and emit a `metrics.test_run` audit entry.

        The test policy uses the same code path as the
        periodic export tick. The operator panel calls it from
        the `Test export` button.
        """

        return await self._exporter.test_export(
            organization_id=organization_id,
            actor=actor,
            actor_role=actor_role,
        )


__all__ = [
    "ExportPolicyAcceptanceRequired",
    "ExportPolicyValidationError",
    "MetricsExportService",
    "verify_scrape_token",
]
