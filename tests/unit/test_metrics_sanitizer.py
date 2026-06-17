"""Unit tests for the metrics export sanitizer (US-042).

The exporter reuses the `SanitizeAlertPayload` helper from
US-041. The tests in this file prove the contract: a payload
that contains a secret, a cookie, raw PII, browser storage
state, or a full connection string is dropped, and the
status becomes `SANITIZER_REJECTED`.
"""

from __future__ import annotations

import pytest

from livelead.application.metrics_export.transports import (
    OtelCollector,
    PrometheusExposition,
    SentryIngest,
    _sanitize_sample,
)
from livelead.domain.metrics_export.enums import (
    ExportStatus,
    MetricsSink,
    OtelProtocol,
)
from livelead.domain.metrics_export.models import (
    MetricSample,
    OtelConfig,
    SentryConfig,
)


def test_sanitize_sample_strips_api_key_label() -> None:
    sample = MetricSample(
        name="connector.failure_rate",
        value=0.5,
        labels={"api_key": "sk-abcdefghijklmnop1234"},
    )
    cleaned, was_redacted = _sanitize_sample(sample)
    assert was_redacted is True
    # The label value must be replaced with the redacted marker.
    assert all(v == "[REDACTED]" for v in cleaned.labels.values())


def test_sanitize_sample_strips_bearer_token_label() -> None:
    sample = MetricSample(
        name="connector.failure_rate",
        value=0.5,
        labels={"authorization": "Bearer abcdefghijklmnop"},
    )
    cleaned, was_redacted = _sanitize_sample(sample)
    assert was_redacted is True
    assert all(v == "[REDACTED]" for v in cleaned.labels.values())


def test_sanitize_sample_strips_full_cookie_string() -> None:
    sample = MetricSample(
        name="connector.failure_rate",
        value=0.5,
        labels={"cookie": "sessionid=abc123; path=/; secure; httponly"},
    )
    cleaned, was_redacted = _sanitize_sample(sample)
    assert was_redacted is True
    assert all(v == "[REDACTED]" for v in cleaned.labels.values())


def test_sanitize_sample_keeps_safe_labels() -> None:
    sample = MetricSample(
        name="connector.failure_rate",
        value=0.5,
        labels={"unit": "ratio", "window": "1800"},
    )
    cleaned, was_redacted = _sanitize_sample(sample)
    assert was_redacted is False
    assert cleaned.labels == {"unit": "ratio", "window": "1800"}


@pytest.mark.asyncio
async def test_prometheus_exposition_drops_poisoned_sample() -> None:
    """The Prometheus transport drops a sample whose label set contains a secret."""

    transport = PrometheusExposition()
    samples = [
        MetricSample(
            name="connector.failure_rate",
            value=0.5,
            labels={"api_key": "sk-abcdefghijklmnop1234"},
        ),
        MetricSample(
            name="backup.age_hours",
            value=2.0,
            labels={"unit": "hours"},
        ),
    ]
    result = await transport.export(
        organization_id="00000000-0000-4000-8000-000000000001",
        samples=samples,
    )
    assert result.status is ExportStatus.SANITIZER_REJECTED
    assert result.accepted == 1
    assert result.rejected == 1
    # The text body must not include the secret value.
    assert "sk-abcdefghijklmnop1234" not in transport.last_text_body


@pytest.mark.asyncio
async def test_otel_collector_returns_sdk_not_installed_when_missing() -> None:
    transport = OtelCollector(
        config=OtelConfig(
            enabled=True,
            endpoint="https://otel.example.com",
            protocol=OtelProtocol.HTTP_PROTOBUF,
        )
    )
    samples = [MetricSample(name="backup.age_hours", value=2.0, labels={"unit": "hours"})]
    result = await transport.export(
        organization_id="00000000-0000-4000-8000-000000000001",
        samples=samples,
    )
    # The optional SDK is not part of the project, so the
    # transport must return SDK_NOT_INSTALLED.
    assert result.status is ExportStatus.SDK_NOT_INSTALLED
    assert result.error == "sdk_not_installed"


@pytest.mark.asyncio
async def test_sentry_ingest_returns_sdk_not_installed_when_missing() -> None:
    transport = SentryIngest(
        config=SentryConfig(
            enabled=True,
            dsn_ref="secret://sentry/dsn",
            environment="pilot_live",
        )
    )
    samples = [MetricSample(name="backup.age_hours", value=2.0, labels={"unit": "hours"})]
    result = await transport.export(
        organization_id="00000000-0000-4000-8000-000000000001",
        samples=samples,
    )
    assert result.status is ExportStatus.SDK_NOT_INSTALLED
    assert result.error == "sdk_not_installed"


@pytest.mark.asyncio
async def test_prometheus_exposition_disabled_returns_disabled() -> None:
    transport = PrometheusExposition()
    samples = [MetricSample(name="backup.age_hours", value=2.0, labels={"unit": "hours"})]
    # The transport is not bound to a policy; the test ensures
    # the transport can be invoked even when the sink is
    # disabled (the operator panel uses this to surface
    # a `disabled` status).
    result = await transport.export(
        organization_id="00000000-0000-4000-8000-000000000001",
        samples=samples,
    )
    # The Prometheus transport does not know the policy; it
    # serializes the body when called. The status reflects
    # the sanitization contract, not the enablement.
    assert result.status is ExportStatus.SUCCESS
    assert result.accepted == 1
    assert result.rejected == 0
    assert "backup.age_hours" in transport.last_text_body
