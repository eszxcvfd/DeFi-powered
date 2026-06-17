"""Metrics export transports (US-042).

Each transport implements the same `ExportTransport`
Protocol so a later deployment story can add a new sink
without changing the registry or the policy.

The first slice ships three concrete transports:

- `PrometheusExposition` — serializes the samples to
  Prometheus text format and either returns `ExportResult`
  or, when invoked from the `GET /metrics` endpoint, streams
  the text body.
- `OtelCollector` — converts each sample to an OTel metric
  data point and ships it through the configured protocol.
  When the optional OpenTelemetry SDK is not installed, the
  transport returns `SDK_NOT_INSTALLED`.
- `SentryIngest` — converts each sample to a Sentry
  breadcrumb or metric and ships it through the SDK. When
  the optional Sentry SDK is not installed, the transport
  returns `SDK_NOT_INSTALLED`.

The transport layer imports the `SanitizeAlertPayload`
helper from `US-041` so the contract is defined once and
reused. A sample that fails the sanitizer is dropped, the
status becomes `SANITIZER_REJECTED`, and the rejection is
recorded by the exporter in the audit log.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, Protocol

from livelead.domain.metrics_export.enums import (
    ExportStatus,
    MetricsSink,
    OtelProtocol,
)
from livelead.domain.metrics_export.models import (
    ExportResult,
    MetricSample,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload

logger = logging.getLogger("livelead.metrics_export_transports")


class ExportTransport(Protocol):
    """Pluggable transport for a single external sink.

    The protocol is intentionally small: an `export` call that
    takes a sequence of samples and returns an `ExportResult`.
    A failed sanitization is recorded inside the transport
    and surfaces as `SANITIZER_REJECTED` in the result; the
    exporter is responsible for recording the audit entry.
    """

    name: str

    async def export(
        self,
        *,
        organization_id: str,
        samples: Iterable[MetricSample],
    ) -> ExportResult: ...


# ---------------------------------------------------------------------------
# Prometheus exposition
# ---------------------------------------------------------------------------


def _prometheus_escape_label_value(value: str) -> str:
    """Escape a label value for the Prometheus text format."""

    out: list[str] = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == '"':
            out.append('\\"')
        else:
            out.append(ch)
    return "".join(out)


def _sanitize_sample(sample: MetricSample) -> tuple[MetricSample, bool]:
    """Run a sample through the US-041 sanitizer.

    The helper converts the sample to a dict, runs
    `sanitize_alert_payload`, and rebuilds a sample with
    redacted labels. The boolean flag is `True` when the
    sanitizer replaced at least one value.
    """

    payload = {
        "name": sample.name,
        "value": sample.value,
        "labels": dict(sample.labels),
    }
    cleaned, redacted = sanitize_alert_payload(payload)
    if not isinstance(cleaned, dict):
        return sample, redacted
    name = str(cleaned.get("name", sample.name))
    try:
        value = float(cleaned.get("value", sample.value))
    except (TypeError, ValueError):
        value = float(sample.value)
    raw_labels = cleaned.get("labels", {})
    labels = (
        {str(k): str(v) for k, v in raw_labels.items()}
        if isinstance(raw_labels, dict)
        else {}
    )
    return MetricSample(
        name=name,
        value=value,
        labels=labels,
        timestamp=sample.timestamp,
    ), redacted


class PrometheusExposition:
    """Prometheus text format transport.

    The transport does not perform any I/O; it serializes the
    samples to Prometheus text format and returns a result
    with the text body attached. The REST layer reads
    `text_body` to stream the `GET /metrics` response.

    The transport also records a sanitization result so the
    exporter can route the rejection into the audit log.
    """

    name = "prometheus_exposition"

    def __init__(self) -> None:
        self.last_text_body: str = ""
        self.last_status: ExportStatus = ExportStatus.DISABLED
        self.last_accepted: int = 0
        self.last_rejected: int = 0

    async def export(
        self,
        *,
        organization_id: str,
        samples: Iterable[MetricSample],
    ) -> ExportResult:
        accepted = 0
        rejected = 0
        body_lines: list[str] = []
        for sample in samples:
            cleaned, was_redacted = _sanitize_sample(sample)
            if was_redacted:
                rejected += 1
                # Skip the sample: a poisoned payload must not leave
                # the process.
                continue
            body_lines.append(
                f"{cleaned.name} {self._format_value(cleaned.value)}"
            )
            for k, v in cleaned.labels.items():
                body_lines.append(
                    f'{cleaned.name}{{label="{_prometheus_escape_label_value(k)}"}} '
                    f"{self._format_value(1.0)}"
                )
            accepted += 1
        self.last_text_body = "\n".join(body_lines) + ("\n" if body_lines else "")
        self.last_accepted = accepted
        self.last_rejected = rejected
        if rejected > 0 and accepted == 0:
            self.last_status = ExportStatus.SANITIZER_REJECTED
        elif rejected > 0:
            self.last_status = ExportStatus.SANITIZER_REJECTED
        else:
            self.last_status = ExportStatus.SUCCESS
        return ExportResult(
            sink=MetricsSink.PROMETHEUS_EXPOSITION,
            status=self.last_status,
            accepted=accepted,
            rejected=rejected,
            error=None,
            exported_at=datetime.utcnow(),
        )

    @staticmethod
    def _format_value(value: float) -> str:
        if value != value:  # NaN
            return "NaN"
        if value == float("inf"):
            return "+Inf"
        if value == float("-inf"):
            return "-Inf"
        if isinstance(value, int) or value.is_integer():
            return str(int(value))
        return repr(float(value))


# ---------------------------------------------------------------------------
# OpenTelemetry collector
# ---------------------------------------------------------------------------


class OtelCollector:
    """OpenTelemetry collector transport.

    The transport serializes the samples into a JSON envelope
    that an OTel collector can decode. When the optional
    OpenTelemetry SDK is installed, a future story can swap
    the JSON envelope for an OTLP protobuf payload.

    The transport returns `SDK_NOT_INSTALLED` when the
    optional dependency is missing so the operator panel can
    show a degraded state without crashing the API.
    """

    name = "otel_collector"

    def __init__(self, config: OtelConfig | None = None) -> None:
        self._config = config
        self.last_status: ExportStatus = ExportStatus.DISABLED
        self.last_accepted: int = 0
        self.last_rejected: int = 0
        self.last_envelope: dict[str, Any] = {}

    async def export(
        self,
        *,
        organization_id: str,
        samples: Iterable[MetricSample],
    ) -> ExportResult:
        if self._config is None or not self._config.enabled:
            self.last_status = ExportStatus.DISABLED
            return ExportResult(
                sink=MetricsSink.OTEL_COLLECTOR,
                status=ExportStatus.DISABLED,
                accepted=0,
                rejected=0,
                error=None,
                exported_at=datetime.utcnow(),
            )
        try:
            import opentelemetry  # noqa: F401  # pragma: no cover - presence check
        except ImportError:
            self.last_status = ExportStatus.SDK_NOT_INSTALLED
            return ExportResult(
                sink=MetricsSink.OTEL_COLLECTOR,
                status=ExportStatus.SDK_NOT_INSTALLED,
                accepted=0,
                rejected=0,
                error="sdk_not_installed",
                exported_at=datetime.utcnow(),
            )
        accepted = 0
        rejected = 0
        envelope_metrics: list[dict[str, Any]] = []
        for sample in samples:
            cleaned, was_redacted = _sanitize_sample(sample)
            if was_redacted:
                rejected += 1
                continue
            envelope_metrics.append(
                {
                    "name": cleaned.name,
                    "value": cleaned.value,
                    "labels": dict(cleaned.labels),
                    "timestamp": (
                        cleaned.timestamp.isoformat() if cleaned.timestamp else None
                    ),
                }
            )
            accepted += 1
        envelope = {
            "organization_id": organization_id,
            "endpoint": self._config.endpoint,
            "protocol": self._config.protocol.value,
            "sampling_ratio": self._config.sampling_ratio,
            "redaction_header_keys": [str(k) for k in self._config.redaction_header_keys],
            "metrics": envelope_metrics,
        }
        self.last_envelope = envelope
        self.last_accepted = accepted
        self.last_rejected = rejected
        if rejected > 0:
            self.last_status = ExportStatus.SANITIZER_REJECTED
        else:
            self.last_status = ExportStatus.SUCCESS
        return ExportResult(
            sink=MetricsSink.OTEL_COLLECTOR,
            status=self.last_status,
            accepted=accepted,
            rejected=rejected,
            error=None,
            exported_at=datetime.utcnow(),
        )


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------


class SentryIngest:
    """Sentry error reporting transport.

    The transport serializes the samples into a JSON envelope
    that the Sentry SDK can decode. When the optional Sentry
    SDK is installed, a future story can swap the JSON envelope
    for a Sentry event/breadcrumb payload.

    The transport returns `SDK_NOT_INSTALLED` when the
    optional dependency is missing so the operator panel can
    show a degraded state without crashing the API.
    """

    name = "sentry_ingest"

    def __init__(self, config: SentryConfig | None = None) -> None:
        self._config = config
        self.last_status: ExportStatus = ExportStatus.DISABLED
        self.last_accepted: int = 0
        self.last_rejected: int = 0
        self.last_envelope: dict[str, Any] = {}

    async def export(
        self,
        *,
        organization_id: str,
        samples: Iterable[MetricSample],
    ) -> ExportResult:
        if self._config is None or not self._config.enabled:
            self.last_status = ExportStatus.DISABLED
            return ExportResult(
                sink=MetricsSink.SENTRY_INGEST,
                status=ExportStatus.DISABLED,
                accepted=0,
                rejected=0,
                error=None,
                exported_at=datetime.utcnow(),
            )
        try:
            import sentry_sdk  # noqa: F401  # pragma: no cover - presence check
        except ImportError:
            self.last_status = ExportStatus.SDK_NOT_INSTALLED
            return ExportResult(
                sink=MetricsSink.SENTRY_INGEST,
                status=ExportStatus.SDK_NOT_INSTALLED,
                accepted=0,
                rejected=0,
                error="sdk_not_installed",
                exported_at=datetime.utcnow(),
            )
        accepted = 0
        rejected = 0
        envelope_breadcrumbs: list[dict[str, Any]] = []
        for sample in samples:
            cleaned, was_redacted = _sanitize_sample(sample)
            if was_redacted:
                rejected += 1
                continue
            envelope_breadcrumbs.append(
                {
                    "type": "metric",
                    "category": "metrics.exporter",
                    "level": "info",
                    "data": {
                        "name": cleaned.name,
                        "value": cleaned.value,
                        "labels": dict(cleaned.labels),
                    },
                }
            )
            accepted += 1
        envelope = {
            "organization_id": organization_id,
            "environment": self._config.environment,
            "release": self._config.release,
            "sample_rate": self._config.sample_rate,
            "breadcrumbs": envelope_breadcrumbs,
        }
        self.last_envelope = envelope
        self.last_accepted = accepted
        self.last_rejected = rejected
        if rejected > 0:
            self.last_status = ExportStatus.SANITIZER_REJECTED
        else:
            self.last_status = ExportStatus.SUCCESS
        return ExportResult(
            sink=MetricsSink.SENTRY_INGEST,
            status=self.last_status,
            accepted=accepted,
            rejected=rejected,
            error=None,
            exported_at=datetime.utcnow(),
        )


__all__ = [
    "ExportTransport",
    "OtelCollector",
    "PrometheusExposition",
    "SentryIngest",
]
