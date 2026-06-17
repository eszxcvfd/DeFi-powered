"""Connector health application service (US-046).

Owns the bounded connector health path. The
service is the only place that mutates
`connector_health_snapshots` and
`connector_health_errors` and emits the
`connector.health.*` audit entries; the REST
layer calls it from the request handlers.

The service reuses the `SanitizeAlertPayload`
helper from `US-041` for every snapshot and audit
payload. The bounded window is enforced by the
`EnvironmentMode` shipped by `US-040` (max 24
hours in `pilot_live`, max 1 hour in `test_like`).
The `MetricRegistry` extension from `US-042` and
the `AlertMetric` enum extension from `US-041`
keep the bounded signals aligned with the
external metrics pipeline and the alert
evaluator.
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
from livelead.application.connector_health.computer import (
    bounded_window as _bounded_window,
    classify_status as _classify_status,
    derive_metrics as _derive_metrics,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthError,
    ConnectorHealthMetrics,
    ConnectorHealthSnapshot,
    ConnectorHealthSummaryEntry,
    ConnectorHealthThresholds,
    ConnectorHealthWindow,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.domain.sources.models import ConnectorType
from livelead.infrastructure.db.models import (
    AuditEntryRow,
    SourceRow,
)
from livelead.infrastructure.db.repositories.connector_health import (
    ConnectorHealthErrorRepository,
    ConnectorHealthSnapshotRepository,
)

logger = logging.getLogger("livelead.connector_health_service")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ConnectorHealthError(ValueError):
    """Raised when a bounded connector health
    operation is rejected."""


class ConnectorHealthSourceNotFound(ConnectorHealthError):
    """Raised when the source is missing or out of
    tenant scope."""


class ConnectorHealthInvalidWindow(ConnectorHealthError):
    """Raised when the window is zero, negative,
    or exceeds the `EnvironmentMode` bound."""


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
    thresholds: ConnectorHealthThresholds,
    environment_mode: EnvironmentMode | str,
) -> int:
    """Bound the requested window by the
    `EnvironmentMode` and the closed
    `ConnectorHealthThresholds` defaults.

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
        raise ConnectorHealthInvalidWindow(
            "CONNECTOR_HEALTH_INVALID_WINDOW"
        )
    return bounded


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ConnectorHealthService:
    """Application service for the bounded
    connector health surface.

    The service is the only place that runs a
    bounded per-source computation and persists
    a `ConnectorHealthSnapshot` row. The bounded
    surface is read-only with respect to product
    state; the only mutations are the
    `connector_health_snapshots` and
    `connector_health_errors` rows plus the
    matching `connector.health.*` audit entries.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        snapshot_repo: ConnectorHealthSnapshotRepository | None = None,
        error_repo: ConnectorHealthErrorRepository | None = None,
        thresholds: ConnectorHealthThresholds | None = None,
        environment_mode: EnvironmentMode | str = EnvironmentMode.TEST_LIKE,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._snapshots = (
            snapshot_repo or ConnectorHealthSnapshotRepository(session)
        )
        self._errors = (
            error_repo or ConnectorHealthErrorRepository(session)
        )
        self._thresholds = thresholds or ConnectorHealthThresholds()
        self._environment_mode = environment_mode

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def snapshot_repo(self) -> ConnectorHealthSnapshotRepository:
        return self._snapshots

    @property
    def error_repo(self) -> ConnectorHealthErrorRepository:
        return self._errors

    @property
    def thresholds(self) -> ConnectorHealthThresholds:
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
            raise ConnectorHealthSourceNotFound(
                "CONNECTOR_HEALTH_SOURCE_NOT_FOUND"
            )
        return row

    async def list_sources(
        self,
        organization_id: UUID | str,
    ) -> list[SourceRow]:
        result = await self._session.execute(
            select(SourceRow)
            .where(SourceRow.organization_id == str(organization_id))
            .order_by(SourceRow.domain)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    async def compute_snapshot(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
        window_seconds: int | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> ConnectorHealthSnapshot:
        """Run a bounded per-source computation and
        persist the `ConnectorHealthSnapshot` row.

        The bounded path reads the
        `audit_entries` rows for the source,
        derives the closed metrics, classifies the
        status, and emits a
        `connector.health.snapshot.computed` audit
        entry. The bounded window is enforced by
        the `EnvironmentMode` from `US-040`.
        """

        org = str(organization_id)
        source = await self._resolve_source(org, source_id)
        bounded_seconds = _bounded_window_seconds(
            requested=int(window_seconds or 0),
            thresholds=self._thresholds,
            environment_mode=self._environment_mode,
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        window = _bounded_window(
            now=now, window_seconds=bounded_seconds
        )
        try:
            connector_type = ConnectorType(source.connector_type)
        except ValueError:
            connector_type = ConnectorType.OFFICIAL_API

        rows = await self._collect_audit_rows(
            organization_id=org,
            source_id=str(source.id),
            window=window,
        )
        metrics = _derive_metrics(
            audit_rows=rows,
            window=window,
            thresholds=self._thresholds,
        )
        status = _classify_status(
            metrics=metrics,
            thresholds=self._thresholds,
        )
        correlation_id = str(uuid4())
        snapshot = await self._snapshots.add(
            organization_id=org,
            source_id=str(source.id),
            connector_type=connector_type,
            window_start=window.start,
            window_end=window.end,
            total_runs=metrics.total_runs,
            success_count=metrics.success_count,
            failure_count=metrics.failure_count,
            success_rate=metrics.success_rate,
            p50_latency_ms=metrics.p50_latency_ms,
            p95_latency_ms=metrics.p95_latency_ms,
            captcha_count=metrics.captcha_count,
            captcha_rate=metrics.captcha_rate,
            last_run_at=metrics.last_run_at,
            last_error_code=metrics.last_error_code,
            last_error_message=metrics.last_error_message,
            status=status,
            audit_correlation_id=correlation_id,
            max_error_message_length=(
                self._thresholds.max_error_message_length
            ),
        )
        if metrics.failure_count > 0 and metrics.last_error_code:
            await self._errors.add(
                organization_id=org,
                source_id=str(source.id),
                error_code=metrics.last_error_code,
                error_message=metrics.last_error_message or "",
                first_seen_at=window.start,
                last_seen_at=metrics.last_run_at or window.end,
                occurrence_count=int(metrics.failure_count),
                audit_correlation_id=correlation_id,
                max_error_message_length=(
                    self._thresholds.max_error_message_length
                ),
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_HEALTH_SNAPSHOT_COMPUTED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_HEALTH_SNAPSHOT,
                target_id=snapshot.id,
                display=f"connector_health_snapshot:{source.id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.health.compute",
            ),
            metadata=_safe_metadata(
                {
                    "source_id": str(source.id),
                    "connector_type": connector_type.value,
                    "window_start": window.start.isoformat(),
                    "window_end": window.end.isoformat(),
                    "window_seconds": int(bounded_seconds),
                    "total_runs": int(metrics.total_runs),
                    "success_count": int(metrics.success_count),
                    "failure_count": int(metrics.failure_count),
                    "success_rate": float(metrics.success_rate),
                    "p50_latency_ms": float(metrics.p50_latency_ms),
                    "p95_latency_ms": float(metrics.p95_latency_ms),
                    "captcha_count": int(metrics.captcha_count),
                    "captcha_rate": float(metrics.captcha_rate),
                    "status": status.value,
                    "environment_mode": str(
                        self._environment_mode
                    ),
                }
            ),
        )
        return snapshot

    async def _collect_audit_rows(
        self,
        *,
        organization_id: str,
        source_id: str,
        window: ConnectorHealthWindow,
    ) -> list[AuditEntryRow]:
        """Collect the bounded `audit_entries` rows
        for the source.

        The bounded path reads the rows whose
        `metadata_json` contains the `source_id`
        and whose `occurred_at` falls inside the
        window. The bounded path applies the
        closed action filter from the computer so
        the service and the test fixtures read the
        same rows.
        """

        from livelead.domain.audit.enums import AuditAction

        candidate_actions = (
            "discovery.run.completed",
            "discovery.run.succeeded",
            "discovery.run.failed",
            "discovery.run.error",
            "discovery.run.crashed",
            "connector.captcha_detected",
            "browser.captcha_detected",
        )
        result = await self._session.execute(
            select(AuditEntryRow)
            .where(
                and_(
                    AuditEntryRow.organization_id
                    == str(organization_id),
                    AuditEntryRow.occurred_at >= window.start,
                    AuditEntryRow.occurred_at <= window.end,
                    AuditEntryRow.action.in_(candidate_actions),
                )
            )
            .order_by(AuditEntryRow.occurred_at)
        )
        bounded: list[AuditEntryRow] = []
        for row in result.scalars().all():
            try:
                metadata = json.loads(row.metadata_json or "{}")
            except (TypeError, ValueError):
                continue
            if not isinstance(metadata, dict):
                continue
            if str(metadata.get("source_id") or "") == str(source_id):
                bounded.append(row)
        return bounded

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_snapshots(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        status: ConnectorHealthStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorHealthSnapshot], int]:
        return await self._snapshots.list_for_org(
            organization_id,
            source_id=source_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def build_summary(
        self,
        organization_id: UUID | str,
        *,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> list[ConnectorHealthSummaryEntry]:
        """Return the latest snapshot per source
        with the closed thresholds, the current
        values, and the breach flag for the
        operator panel.

        The bounded path emits a
        `connector.health.summary.requested` audit
        entry so the admin audit log filter from
        `US-026` can reason about the bounded
        surface.
        """

        org = str(organization_id)
        sources = await self.list_sources(org)
        snapshots = await self._snapshots.latest_for_org(org)
        latest_by_source: dict[str, ConnectorHealthSnapshot] = {}
        for snapshot in snapshots:
            if snapshot.source_id not in latest_by_source:
                latest_by_source[snapshot.source_id] = snapshot
        entries: list[ConnectorHealthSummaryEntry] = []
        for source in sources:
            snapshot = latest_by_source.get(str(source.id))
            breach = False
            if snapshot is not None:
                breach = bool(
                    snapshot.success_rate
                    < self._thresholds.healthy_min_success_rate
                    or snapshot.captcha_rate
                    > self._thresholds.healthy_max_captcha_rate
                )
            try:
                connector_type = ConnectorType(source.connector_type)
            except ValueError:
                connector_type = ConnectorType.OFFICIAL_API
            entries.append(
                ConnectorHealthSummaryEntry(
                    source_id=str(source.id),
                    source_name=source.name or source.domain or "",
                    connector_type=connector_type,
                    snapshot=snapshot,
                    healthy_min_success_rate=(
                        self._thresholds.healthy_min_success_rate
                    ),
                    degraded_min_success_rate=(
                        self._thresholds.degraded_min_success_rate
                    ),
                    healthy_max_captcha_rate=(
                        self._thresholds.healthy_max_captcha_rate
                    ),
                    degraded_max_captcha_rate=(
                        self._thresholds.degraded_max_captcha_rate
                    ),
                    breach=breach,
                )
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_HEALTH_SUMMARY_REQUESTED,
            target=AuditTarget(
                target_type=AuditTargetType.SYSTEM,
                target_id="connector.health.summary",
                display="connector_health_summary",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.health.summary",
            ),
            metadata=_safe_metadata(
                {
                    "source_count": len(entries),
                    "breach_count": sum(
                        1 for e in entries if e.breach
                    ),
                }
            ),
        )
        return entries

    async def list_recent_errors(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
        *,
        limit: int = 20,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> list[ConnectorHealthError]:
        await self._resolve_source(organization_id, source_id)
        org = str(organization_id)
        bounded_limit = min(
            int(limit), self._thresholds.recent_errors_limit
        )
        errors = await self._errors.list_for_source(
            org, source_id, limit=bounded_limit
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.CONNECTOR_HEALTH_ERRORS_REQUESTED,
            target=AuditTarget(
                target_type=AuditTargetType.CONNECTOR_HEALTH_ERROR,
                target_id=str(source_id),
                display=f"connector_health_errors:{source_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="connector.health.errors",
            ),
            metadata=_safe_metadata(
                {
                    "source_id": str(source_id),
                    "limit": int(bounded_limit),
                    "result_count": len(errors),
                }
            ),
        )
        return errors


__all__ = [
    "ConnectorHealthError",
    "ConnectorHealthInvalidWindow",
    "ConnectorHealthService",
    "ConnectorHealthSourceNotFound",
]
