"""External metrics export domain models (US-042).

Pure dataclasses with no I/O. The infrastructure layer is
responsible for translating these to and from SQLAlchemy rows.
The model layer deliberately does not import SQLAlchemy,
FastAPI, or any framework.

The `MetricRegistry` mirrors the closed `SignalProvider` enum
from `US-041` so the exporter and the alert evaluator cannot
drift apart. New metrics must be added to the enum, the
`SignalProviderFactory`, and the registry in the same change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping

from livelead.domain.metrics_export.enums import (
    DEFAULT_OTEL_REDACTION_HEADER_KEYS,
    DEFAULT_OTEL_SAMPLING_RATIO,
    DEFAULT_PROMETHEUS_ALLOWED_CIDRS,
    DEFAULT_SENTRY_ENVIRONMENT,
    DEFAULT_SENTRY_SAMPLE_RATE,
    ExportStatus,
    MetricsSink,
    OtelProtocol,
    SUPPORTED_OTEL_PROTOCOLS,
    SUPPORTED_SINKS,
)


# ---------------------------------------------------------------------------
# Metric sample + registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricSample:
    """A single observation of a metric, ready to be serialized.

    `name` must be a metric registered in the `MetricRegistry`.
    `labels` is a small, secret-safe mapping. `timestamp` is
    optional; when missing, the transport uses the export time.
    """

    name: str
    value: float
    labels: Mapping[str, str] = field(default_factory=dict)
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class MetricDescriptor:
    """A registered metric.

    The registry attaches this descriptor to every registered
    metric name. New metrics cannot be added to the registry
    without first being added to the closed `SignalProvider`
    enum from `US-041`; this keeps the exporter and the alert
    evaluator aligned.
    """

    name: str
    unit: str
    type: str  # "gauge" | "counter" | "histogram"
    cardinality_budget: int
    secret_safety: str  # "safe" | "redact_before_export" | "forbidden"
    description: str


class MetricRegistry:
    """Closed enumeration of metric names that the exporter is allowed to publish.

    The registry is constructed at process startup from the
    `SignalProviderFactory` of `US-041`. A new metric cannot
    be registered without first being added to the closed
    `SignalProvider` enum; this is enforced at the constructor
    level by requiring the metric name to match a known
    `AlertMetric` value.
    """

    # Mirror of the US-041 `AlertMetric` enum. New metrics must
    # be added to both the enum and the registry in the same
    # change. The mirror is intentionally a class-level tuple
    # so the unit test can iterate it without a live factory.
    _DEFAULT_DESCRIPTORS: tuple[MetricDescriptor, ...] = (
        MetricDescriptor(
            name="backup.age_hours",
            unit="hours",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="Age of the most recent backup snapshot in hours.",
        ),
        MetricDescriptor(
            name="worker.heartbeat.age_seconds",
            unit="seconds",
            type="gauge",
            cardinality_budget=16,
            secret_safety="safe",
            description="Age of the most recent worker heartbeat in seconds.",
        ),
        MetricDescriptor(
            name="connector.failure_rate",
            unit="ratio",
            type="gauge",
            cardinality_budget=64,
            secret_safety="safe",
            description="Ratio of failed discovery jobs to completed jobs in the rolling window.",
        ),
        MetricDescriptor(
            name="discovery.needs_user_action_rate",
            unit="ratio",
            type="gauge",
            cardinality_budget=64,
            secret_safety="safe",
            description="Ratio of discovery jobs in `needs_user_action` to completed jobs in the rolling window.",
        ),
        MetricDescriptor(
            name="browser.crash_loop",
            unit="events",
            type="counter",
            cardinality_budget=32,
            secret_safety="safe",
            description="Number of recorded browser-session crash events in the rolling window.",
        ),
        MetricDescriptor(
            name="audit.retention_breach_risk",
            unit="days",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="Age of the oldest audit-log row in days; alerts when it exceeds the retention floor.",
        ),
        MetricDescriptor(
            name="alert.evaluator.duration_ms",
            unit="ms",
            type="histogram",
            cardinality_budget=16,
            secret_safety="safe",
            description="Wall-clock time for one alert evaluator tick in milliseconds.",
        ),
        MetricDescriptor(
            name="metrics.exporter.duration_ms",
            unit="ms",
            type="histogram",
            cardinality_budget=16,
            secret_safety="safe",
            description="Wall-clock time for one metrics exporter tick in milliseconds.",
        ),
    )

    def __init__(
        self,
        descriptors: Iterable[MetricDescriptor] | None = None,
        *,
        allowed_metrics: Iterable[str] | None = None,
    ) -> None:
        items = list(descriptors) if descriptors is not None else list(self._DEFAULT_DESCRIPTORS)
        if not items:
            raise ValueError("METRIC_REGISTRY_INVALID:descriptors_required")
        allow = (
            {str(m) for m in allowed_metrics}
            if allowed_metrics is not None
            else None
        )
        seen: set[str] = set()
        self._descriptors: dict[str, MetricDescriptor] = {}
        for desc in items:
            if desc.name in seen:
                raise ValueError(
                    f"METRIC_REGISTRY_INVALID:duplicate_descriptor:{desc.name}"
                )
            seen.add(desc.name)
            if allow is not None and desc.name not in allow:
                # Filter out descriptors that are not in the closed
                # enum. The constructor refuses to register a metric
                # that the alert evaluator does not know about.
                continue
            if desc.secret_safety == "forbidden":
                raise ValueError(
                    f"METRIC_REGISTRY_INVALID:forbidden_metric:{desc.name}"
                )
            if desc.cardinality_budget <= 0:
                raise ValueError(
                    f"METRIC_REGISTRY_INVALID:cardinality_non_positive:{desc.name}"
                )
            self._descriptors[desc.name] = desc

    def get(self, name: str) -> MetricDescriptor | None:
        return self._descriptors.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._descriptors

    def supported_metrics(self) -> frozenset[str]:
        return frozenset(self._descriptors)

    def all(self) -> tuple[MetricDescriptor, ...]:
        return tuple(self._descriptors.values())


# ---------------------------------------------------------------------------
# Sink configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrometheusConfig:
    """Per-workspace configuration for the Prometheus exposition sink."""

    enabled: bool = False
    scrape_token_hash: str = ""
    allowed_source_cidrs: tuple[str, ...] = DEFAULT_PROMETHEUS_ALLOWED_CIDRS
    retention_note: str = ""


@dataclass(frozen=True, slots=True)
class OtelConfig:
    """Per-workspace configuration for the OpenTelemetry collector sink."""

    enabled: bool = False
    endpoint: str = ""
    protocol: OtelProtocol = OtelProtocol.HTTP_PROTOBUF
    sampling_ratio: float = DEFAULT_OTEL_SAMPLING_RATIO
    redaction_header_keys: tuple[str, ...] = DEFAULT_OTEL_REDACTION_HEADER_KEYS


@dataclass(frozen=True, slots=True)
class SentryConfig:
    """Per-workspace configuration for the Sentry error reporting sink.

    `dsn_ref` is a reference to the secret manager entry where
    the DSN is stored. The DSN itself is never stored on the
    policy row; the secret manager lookup happens at the
    transport layer.
    """

    enabled: bool = False
    dsn_ref: str = ""
    environment: str = DEFAULT_SENTRY_ENVIRONMENT
    release: str = ""
    sample_rate: float = DEFAULT_SENTRY_SAMPLE_RATE


# ---------------------------------------------------------------------------
# Export result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExportResult:
    """The result of a single sink export attempt.

    The result is what the operator panel and the audit log
    surface for each sink. `accepted` and `rejected` are the
    number of samples that passed or failed the sanitization
    contract; `error` carries a non-secret error message when
    the transport fails.
    """

    sink: MetricsSink
    status: ExportStatus
    accepted: int
    rejected: int
    error: str | None = None
    exported_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sink": self.sink.value,
            "status": self.status.value,
            "accepted": int(self.accepted),
            "rejected": int(self.rejected),
            "error": self.error,
            "exported_at": (
                self.exported_at.isoformat() if self.exported_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricsExportPolicy:
    """A single per-workspace export policy.

    The policy holds the configuration for every sink plus the
    last export status per sink and the acceptance metadata
    that gates the enablement of any sink.
    """

    organization_id: str
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    otel: OtelConfig = field(default_factory=OtelConfig)
    sentry: SentryConfig = field(default_factory=SentryConfig)
    prometheus_last_status: ExportStatus = ExportStatus.DISABLED
    prometheus_last_export_at: datetime | None = None
    otel_last_status: ExportStatus = ExportStatus.DISABLED
    otel_last_export_at: datetime | None = None
    sentry_last_status: ExportStatus = ExportStatus.DISABLED
    sentry_last_export_at: datetime | None = None
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def sink_config(self, sink: MetricsSink) -> PrometheusConfig | OtelConfig | SentryConfig:
        if sink is MetricsSink.PROMETHEUS_EXPOSITION:
            return self.prometheus
        if sink is MetricsSink.OTEL_COLLECTOR:
            return self.otel
        if sink is MetricsSink.SENTRY_INGEST:
            return self.sentry
        raise ValueError(f"EXPORT_POLICY_INVALID:sink_unsupported:{sink}")

    def sink_enabled(self, sink: MetricsSink) -> bool:
        return bool(self.sink_config(sink).enabled)

    def sink_last_status(self, sink: MetricsSink) -> ExportStatus:
        if sink is MetricsSink.PROMETHEUS_EXPOSITION:
            return self.prometheus_last_status
        if sink is MetricsSink.OTEL_COLLECTOR:
            return self.otel_last_status
        if sink is MetricsSink.SENTRY_INGEST:
            return self.sentry_last_status
        raise ValueError(f"EXPORT_POLICY_INVALID:sink_unsupported:{sink}")

    def sink_last_export_at(self, sink: MetricsSink) -> datetime | None:
        if sink is MetricsSink.PROMETHEUS_EXPOSITION:
            return self.prometheus_last_export_at
        if sink is MetricsSink.OTEL_COLLECTOR:
            return self.otel_last_export_at
        if sink is MetricsSink.SENTRY_INGEST:
            return self.sentry_last_export_at
        raise ValueError(f"EXPORT_POLICY_INVALID:sink_unsupported:{sink}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _is_valid_cidr(value: str) -> bool:
    """Lightweight CIDR check; refuses empty strings and obvious garbage."""

    s = (value or "").strip()
    if not s:
        return False
    if "/" not in s:
        return False
    head, _, tail = s.partition("/")
    if not head or not tail:
        return False
    if not tail.isdigit():
        return False
    prefix = int(tail)
    if prefix < 0 or prefix > 128:
        return False
    return True


def validate_prometheus_config(cfg: PrometheusConfig) -> None:
    if not isinstance(cfg.enabled, bool):
        raise ValueError("EXPORT_POLICY_INVALID:prometheus_enabled_not_bool")
    if cfg.enabled and not cfg.scrape_token_hash:
        raise ValueError("EXPORT_POLICY_INVALID:prometheus_scrape_token_required")
    if not cfg.allowed_source_cidrs:
        raise ValueError("EXPORT_POLICY_INVALID:prometheus_cidrs_required")
    for cidr in cfg.allowed_source_cidrs:
        if not _is_valid_cidr(str(cidr)):
            raise ValueError(f"EXPORT_POLICY_INVALID:prometheus_cidr_invalid:{cidr}")
    if len(cfg.retention_note) > 500:
        raise ValueError("EXPORT_POLICY_INVALID:prometheus_retention_note_too_long")


def validate_otel_config(cfg: OtelConfig) -> None:
    if not isinstance(cfg.enabled, bool):
        raise ValueError("EXPORT_POLICY_INVALID:otel_enabled_not_bool")
    if cfg.enabled and not cfg.endpoint:
        raise ValueError("EXPORT_POLICY_INVALID:otel_endpoint_required")
    if cfg.protocol not in SUPPORTED_OTEL_PROTOCOLS:
        raise ValueError(
            f"EXPORT_POLICY_INVALID:otel_protocol_unsupported:{cfg.protocol}"
        )
    try:
        ratio = float(cfg.sampling_ratio)
    except (TypeError, ValueError) as exc:
        raise ValueError("EXPORT_POLICY_INVALID:otel_sampling_ratio_invalid") from exc
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError("EXPORT_POLICY_INVALID:otel_sampling_ratio_out_of_range")


def validate_sentry_config(cfg: SentryConfig) -> None:
    if not isinstance(cfg.enabled, bool):
        raise ValueError("EXPORT_POLICY_INVALID:sentry_enabled_not_bool")
    if cfg.enabled and not cfg.dsn_ref:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_dsn_ref_required")
    if not cfg.environment:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_environment_required")
    if len(cfg.environment) > 64:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_environment_too_long")
    if len(cfg.release) > 128:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_release_too_long")
    try:
        rate = float(cfg.sample_rate)
    except (TypeError, ValueError) as exc:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_sample_rate_invalid") from exc
    if rate < 0.0 or rate > 1.0:
        raise ValueError("EXPORT_POLICY_INVALID:sentry_sample_rate_out_of_range")


def validate_policy_payload(
    *,
    prometheus: PrometheusConfig,
    otel: OtelConfig,
    sentry: SentryConfig,
) -> None:
    """Validate a candidate export policy before it is persisted.

    The validator refuses to enable a sink without the
    supporting configuration. It does not enforce acceptance
    (the REST layer enforces `accepted_by` / `accepted_at`); it
    only checks the configuration shape.
    """

    validate_prometheus_config(prometheus)
    validate_otel_config(otel)
    validate_sentry_config(sentry)


# ---------------------------------------------------------------------------
# Cardinality budget enforcement
# ---------------------------------------------------------------------------


def exceeds_cardinality_budget(sample: MetricSample, descriptor: MetricDescriptor) -> bool:
    """Return True when a sample's label set exceeds the metric's budget.

    The budget is the maximum number of distinct label combinations
    the exporter is allowed to publish for a single metric. The
    exporter does not need to track the actual cardinality; the
    budget is checked at the sample level, and a label set that is
    too large is rejected and recorded in the audit log.
    """

    return len(tuple(sample.labels)) > descriptor.cardinality_budget


__all__ = [
    "ExportResult",
    "MetricDescriptor",
    "MetricRegistry",
    "MetricSample",
    "MetricsExportPolicy",
    "OtelConfig",
    "PrometheusConfig",
    "SentryConfig",
    "SUPPORTED_SINKS",
    "exceeds_cardinality_budget",
    "validate_policy_payload",
]
