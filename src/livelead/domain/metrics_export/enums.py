"""External metrics export enums (US-042).

Closed enumerations for sinks, transport names, and export
statuses. The values are persisted as strings so the migration
can use stable SQL `VARCHAR` columns; the application layer
normalises back to these enums at the boundary.

The enumerations deliberately mirror the pattern used by the
`US-041` alerting slice (`AlertMetric`, `AlertChannel`,
`AlertSeverity`) so the same operator grammar and the same
sanitization helper can be reused.
"""

from __future__ import annotations

from enum import StrEnum


class MetricsSink(StrEnum):
    """Closed set of external sinks the first slice supports.

    A sink is opt-in: by default all three are disabled. Owners
    and admins enable a sink through the policy endpoints; the
    enablement is recorded through `accepted_by` and
    `accepted_at` on the policy row.
    """

    PROMETHEUS_EXPOSITION = "prometheus_exposition"
    OTEL_COLLECTOR = "otel_collector"
    SENTRY_INGEST = "sentry_ingest"


class ExportStatus(StrEnum):
    """Result of a single export attempt.

    The status is what the operator panel and the audit log
    surface for each sink. `disabled` is returned when the
    sink is intentionally turned off; `sdk_not_installed` is
    returned when the optional dependency for the sink is
    not present in the runtime.
    """

    SUCCESS = "success"
    SANITIZER_REJECTED = "sanitizer_rejected"
    TRANSPORT_ERROR = "transport_error"
    DISABLED = "disabled"
    SDK_NOT_INSTALLED = "sdk_not_installed"


class OtelProtocol(StrEnum):
    """Transport protocol for the OpenTelemetry collector sink.

    `http/protobuf` is the default for the first slice and is
    the only protocol that the test transport implements.
    """

    HTTP_PROTOBUF = "http/protobuf"
    GRPC = "grpc"


SUPPORTED_SINKS: frozenset[MetricsSink] = frozenset(MetricsSink)
SUPPORTED_OTEL_PROTOCOLS: frozenset[OtelProtocol] = frozenset(OtelProtocol)

# Default CIDR allowlist for the Prometheus exposition endpoint. The
# default keeps the endpoint local-only; an owner/admin must add
# additional CIDRs to open the endpoint to a remote scraper.
DEFAULT_PROMETHEUS_ALLOWED_CIDRS: tuple[str, ...] = (
    "127.0.0.1/32",
    "::1/128",
)

# Default header keys to redact from the OpenTelemetry export. These
# are the headers the SDK forwards on every request and are the
# most likely place where a secret would leak if the source app
# sets a global header.
DEFAULT_OTEL_REDACTION_HEADER_KEYS: tuple[str, ...] = (
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
)

# Default sampling ratios. The first slice ships conservative
# defaults; owners and admins can tune them per workspace.
DEFAULT_OTEL_SAMPLING_RATIO: float = 0.1
DEFAULT_SENTRY_SAMPLE_RATE: float = 0.2

# Default environment for the Sentry sink. The default follows the
# `US-040` environment modes: `test_like`, `pilot_live`, `paused`.
DEFAULT_SENTRY_ENVIRONMENT: str = "pilot_live"


__all__ = [
    "DEFAULT_OTEL_REDACTION_HEADER_KEYS",
    "DEFAULT_OTEL_SAMPLING_RATIO",
    "DEFAULT_PROMETHEUS_ALLOWED_CIDRS",
    "DEFAULT_SENTRY_ENVIRONMENT",
    "DEFAULT_SENTRY_SAMPLE_RATE",
    "ExportStatus",
    "MetricsSink",
    "OtelProtocol",
    "SUPPORTED_OTEL_PROTOCOLS",
    "SUPPORTED_SINKS",
]
