"""Unit tests for the export policy validation (US-042)."""

from __future__ import annotations

import pytest

from livelead.domain.metrics_export.enums import (
    DEFAULT_OTEL_REDACTION_HEADER_KEYS,
    DEFAULT_OTEL_SAMPLING_RATIO,
    DEFAULT_PROMETHEUS_ALLOWED_CIDRS,
    DEFAULT_SENTRY_ENVIRONMENT,
    DEFAULT_SENTRY_SAMPLE_RATE,
    ExportStatus,
    MetricsSink,
    OtelProtocol,
)
from livelead.domain.metrics_export.models import (
    MetricsExportPolicy,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
    validate_policy_payload,
)


def _empty_policy() -> MetricsExportPolicy:
    return MetricsExportPolicy(organization_id="00000000-0000-4000-8000-000000000001")


def test_default_policy_has_every_sink_disabled() -> None:
    policy = _empty_policy()
    for sink in MetricsSink:
        assert policy.sink_enabled(sink) is False
        assert policy.sink_last_status(sink) is ExportStatus.DISABLED
        assert policy.sink_last_export_at(sink) is None


def test_sink_enabled_and_status_dispatch() -> None:
    prom = PrometheusConfig(enabled=True, scrape_token_hash="abc")
    otel = OtelConfig(enabled=True, endpoint="https://otel.example.com")
    sentry = SentryConfig(enabled=True, dsn_ref="secret://sentry/dsn")
    policy = MetricsExportPolicy(
        organization_id="00000000-0000-4000-8000-000000000001",
        prometheus=prom,
        otel=otel,
        sentry=sentry,
    )
    assert policy.sink_enabled(MetricsSink.PROMETHEUS_EXPOSITION) is True
    assert policy.sink_enabled(MetricsSink.OTEL_COLLECTOR) is True
    assert policy.sink_enabled(MetricsSink.SENTRY_INGEST) is True


def test_validate_policy_payload_accepts_defaults() -> None:
    validate_policy_payload(
        prometheus=PrometheusConfig(),
        otel=OtelConfig(),
        sentry=SentryConfig(),
    )


def test_validate_policy_payload_rejects_prometheus_without_token() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(enabled=True, scrape_token_hash=""),
            otel=OtelConfig(),
            sentry=SentryConfig(),
        )
    assert "EXPORT_POLICY_INVALID:prometheus_scrape_token_required" in str(exc.value)


def test_validate_policy_payload_rejects_invalid_cidr() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(
                enabled=True,
                scrape_token_hash="abc",
                allowed_source_cidrs=("not-a-cidr",),
            ),
            otel=OtelConfig(),
            sentry=SentryConfig(),
        )
    assert "EXPORT_POLICY_INVALID:prometheus_cidr_invalid" in str(exc.value)


def test_validate_policy_payload_rejects_otel_without_endpoint() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(),
            otel=OtelConfig(enabled=True, endpoint=""),
            sentry=SentryConfig(),
        )
    assert "EXPORT_POLICY_INVALID:otel_endpoint_required" in str(exc.value)


def test_validate_policy_payload_rejects_otel_protocol_outside_enum() -> None:
    with pytest.raises(ValueError):
        validate_policy_payload(
            prometheus=PrometheusConfig(),
            otel=OtelConfig(protocol="not-a-protocol"),
            sentry=SentryConfig(),
        )


def test_validate_policy_payload_rejects_otel_sampling_ratio_out_of_range() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(),
            otel=OtelConfig(sampling_ratio=1.5),
            sentry=SentryConfig(),
        )
    assert "EXPORT_POLICY_INVALID:otel_sampling_ratio_out_of_range" in str(exc.value)


def test_validate_policy_payload_rejects_sentry_without_dsn_ref() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(),
            otel=OtelConfig(),
            sentry=SentryConfig(enabled=True, dsn_ref=""),
        )
    assert "EXPORT_POLICY_INVALID:sentry_dsn_ref_required" in str(exc.value)


def test_validate_policy_payload_rejects_sentry_sample_rate_out_of_range() -> None:
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=PrometheusConfig(),
            otel=OtelConfig(),
            sentry=SentryConfig(sample_rate=1.5),
        )
    assert "EXPORT_POLICY_INVALID:sentry_sample_rate_out_of_range" in str(exc.value)


def test_default_constants_match_spec() -> None:
    assert DEFAULT_PROMETHEUS_ALLOWED_CIDRS == ("127.0.0.1/32", "::1/128")
    assert "authorization" in DEFAULT_OTEL_REDACTION_HEADER_KEYS
    assert "cookie" in DEFAULT_OTEL_REDACTION_HEADER_KEYS
    assert DEFAULT_OTEL_SAMPLING_RATIO == 0.1
    assert DEFAULT_SENTRY_SAMPLE_RATE == 0.2
    assert DEFAULT_SENTRY_ENVIRONMENT == "pilot_live"
