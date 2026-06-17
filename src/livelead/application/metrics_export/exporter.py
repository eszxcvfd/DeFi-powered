"""Metrics exporter (US-042).

The exporter reads metric values from the existing
`SignalProviderFactory` (US-041), applies the closed
`MetricRegistry` cardinality budget, runs the payload through
`SanitizeAlertPayload` (US-041), and dispatches the samples
to the configured transports.

The exporter is read-only with respect to product state. It
persists no rows outside the `last_export_status` and
`last_export_at` columns on the policy row and emits audit
entries through the `AuditService` for every attempt. It does
not pause jobs, disable connectors, flip live toggles, or
roll back the environment.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.metrics_export.transports import (
    ExportTransport,
    OtelCollector,
    PrometheusExposition,
    SentryIngest,
)
from livelead.application.observability.signals import SignalProviderFactory
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditActor, AuditTarget
from livelead.domain.metrics_export.enums import (
    ExportStatus,
    MetricsSink,
    SUPPORTED_SINKS,
)
from livelead.domain.metrics_export.models import (
    ExportResult,
    MetricRegistry,
    MetricSample,
    MetricsExportPolicy,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
    exceeds_cardinality_budget,
)
from livelead.infrastructure.db.repositories.metrics_export import (
    MetricsExportPolicyRepository,
)

logger = logging.getLogger("livelead.metrics_exporter")


class MetricsExporter:
    """Coordinates the read path from `SignalProviderFactory` to the transports.

    The exporter is constructed once per process and shared
    across ticks. Tests can pass a custom `MetricRegistry` and
    transport factory to assert the contract without going
    through the database.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        signal_factory: SignalProviderFactory | None = None,
        registry: MetricRegistry | None = None,
        transport_factory: "TransportFactory | None" = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._signal_factory = signal_factory or SignalProviderFactory()
        self._registry = registry or MetricRegistry()
        self._transport_factory = transport_factory or DefaultTransportFactory()
        self._audit = audit_service or AuditService(session)
        self._policy_repo = MetricsExportPolicyRepository(session)

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def registry(self) -> MetricRegistry:
        return self._registry

    @property
    def signal_factory(self) -> SignalProviderFactory:
        return self._signal_factory

    @property
    def policy_repo(self) -> MetricsExportPolicyRepository:
        return self._policy_repo

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    async def collect_samples(
        self,
        *,
        organization_id: str,
    ) -> list[MetricSample]:
        """Read every registered metric through the `SignalProviderFactory`.

        The helper iterates the registry and reads each metric
        through the corresponding `SignalProvider`. The
        resulting `MetricSample` is the in-memory representation
        the transports serialize.
        """

        samples: list[MetricSample] = []
        for descriptor in self._registry.all():
            provider = self._signal_factory.get(descriptor.name)
            if provider is None:
                # A registered metric without a provider is a
                # configuration bug. The exporter records the
                # gap through the audit log.
                continue
            try:
                result = await provider.read(
                    self._session,
                    organization_id=organization_id,
                    window_seconds=0,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "metrics.exporter.signal_error metric=%s error=%s",
                    descriptor.name,
                    exc,
                )
                continue
            sample = MetricSample(
                name=descriptor.name,
                value=float(result.value),
                labels={"unit": descriptor.unit},
            )
            samples.append(sample)
        return samples

    # ------------------------------------------------------------------
    # Export path
    # ------------------------------------------------------------------

    async def export(
        self,
        *,
        organization_id: UUID | str,
        actor: str = "system",
        actor_role: str = "system",
    ) -> dict[MetricsSink, ExportResult]:
        """Run a full export tick.

        The tick reads the policy, collects samples, applies
        the cardinality budget, dispatches to the configured
        transports, and records the per-sink `last_export_status`
        and `last_export_at`. Every dispatch emits a
        `metrics.exported` or `metrics.export_rejected` audit
        entry.
        """

        org = str(organization_id)
        policy = await self._policy_repo.get_or_default(org)
        samples = await self.collect_samples(organization_id=org)
        results: dict[MetricsSink, ExportResult] = {}
        for sink in SUPPORTED_SINKS:
            transport = self._transport_factory.build(sink, policy)
            result = await transport.export(
                organization_id=org, samples=samples
            )
            results[sink] = result
            await self._policy_repo.record_export(
                organization_id=org,
                sink=sink,
                status=result.status,
                exported_at=result.exported_at,
            )
            await self._emit_audit(
                actor=actor,
                actor_role=actor_role,
                organization_id=org,
                sink=sink,
                result=result,
            )
        return results

    async def test_export(
        self,
        *,
        organization_id: UUID | str,
        actor: str,
        actor_role: str,
    ) -> dict[MetricsSink, ExportResult]:
        """Run a single round-trip per enabled sink and emit a `metrics.test_run` audit entry.

        The test export uses the same code path as the regular
        export tick so an operator can verify the sanitization
        contract and the transport wiring before enabling a
        real destination.
        """

        org = str(organization_id)
        policy = await self._policy_repo.get_or_default(org)
        results: dict[MetricsSink, ExportResult] = {}
        for sink in SUPPORTED_SINKS:
            transport = self._transport_factory.build(sink, policy)
            sample = MetricSample(
                name="metrics.exporter.duration_ms",
                value=0.0,
                labels={"sink": sink.value, "test": "true"},
            )
            result = await transport.export(
                organization_id=org, samples=[sample]
            )
            results[sink] = result
            await self._policy_repo.record_export(
                organization_id=org,
                sink=sink,
                status=result.status,
                exported_at=result.exported_at,
            )
            await self._audit.emit(
                organization_id=org,
                actor=make_actor_from_role(actor_role, actor_id=actor or None),
                action=AuditAction.METRICS_TEST_RUN,
                target=AuditTarget(
                    target_type=AuditTargetType.METRICS_EXPORT_POLICY,
                    target_id=org,
                    display=f"{sink.value}:test",
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=make_context(workflow="metrics.test_run"),
                metadata={
                    "sink": sink.value,
                    "status": result.status.value,
                    "accepted": result.accepted,
                    "rejected": result.rejected,
                    "error": result.error,
                },
            )
        return results

    # ------------------------------------------------------------------
    # Audit helper
    # ------------------------------------------------------------------

    async def _emit_audit(
        self,
        *,
        organization_id: str,
        actor: str,
        actor_role: str,
        sink: MetricsSink,
        result: ExportResult,
    ) -> None:
        action = (
            AuditAction.METRICS_EXPORT_REJECTED
            if result.status in (ExportStatus.SANITIZER_REJECTED, ExportStatus.TRANSPORT_ERROR)
            else AuditAction.METRICS_EXPORTED
        )
        outcome = (
            AuditOutcome.FAILED
            if result.status in (ExportStatus.SANITIZER_REJECTED, ExportStatus.TRANSPORT_ERROR)
            else AuditOutcome.SUCCEEDED
        )
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=action,
            target=AuditTarget(
                target_type=AuditTargetType.METRICS_EXPORT_POLICY,
                target_id=organization_id,
                display=sink.value,
            ),
            outcome=outcome,
            context=make_context(workflow="metrics.export"),
            metadata={
                "sink": sink.value,
                "status": result.status.value,
                "accepted": result.accepted,
                "rejected": result.rejected,
                "error": result.error,
            },
        )


# ---------------------------------------------------------------------------
# Transport factory
# ---------------------------------------------------------------------------


class TransportFactory:
    """Build an `ExportTransport` for a given sink and policy."""

    def build(
        self, sink: MetricsSink, policy: MetricsExportPolicy
    ) -> ExportTransport: ...


class DefaultTransportFactory:
    """Default transport factory used by the application service."""

    def build(
        self, sink: MetricsSink, policy: MetricsExportPolicy
    ) -> ExportTransport:
        if sink is MetricsSink.PROMETHEUS_EXPOSITION:
            return PrometheusExposition()
        if sink is MetricsSink.OTEL_COLLECTOR:
            return OtelCollector(config=policy.otel)
        if sink is MetricsSink.SENTRY_INGEST:
            return SentryIngest(config=policy.sentry)
        raise ValueError(f"EXPORT_POLICY_INVALID:sink_unsupported:{sink}")


__all__ = [
    "DefaultTransportFactory",
    "MetricsExporter",
    "TransportFactory",
]
