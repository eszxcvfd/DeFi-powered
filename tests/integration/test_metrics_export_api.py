"""Integration tests for the metrics export policy admin API (US-042)."""

from __future__ import annotations

import pytest


def _owner_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "owner",
    }


def _admin_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "admin",
    }


def _analyst_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "analyst",
    }


def _viewer_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "viewer",
    }


@pytest.mark.asyncio
async def test_get_export_policy_forbidden_for_analyst(migrated_client):
    r = await migrated_client.get(
        "/admin/observability/export-policy", headers=_analyst_headers()
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_export_policy_forbidden_for_viewer(migrated_client):
    r = await migrated_client.get(
        "/admin/observability/export-policy", headers=_viewer_headers()
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_export_policy_owner_returns_defaults(migrated_client):
    r = await migrated_client.get(
        "/admin/observability/export-policy", headers=_owner_headers()
    )
    assert r.status_code == 200
    body = r.json()
    assert body["prometheus"]["enabled"] is False
    assert body["otel"]["enabled"] is False
    assert body["sentry"]["enabled"] is False
    assert body["prometheus_status"]["status"] == "disabled"
    assert body["otel_status"]["status"] == "disabled"
    assert body["sentry_status"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_put_export_policy_rejects_prometheus_without_token(migrated_client):
    payload = {
        "prometheus": {
            "enabled": True,
            "allowed_source_cidrs": ["127.0.0.1/32"],
            "retention_note": "test",
        }
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "prometheus_scrape_token_required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_put_export_policy_enables_prometheus_with_token(migrated_client):
    payload = {
        "prometheus": {
            "enabled": True,
            "allowed_source_cidrs": ["127.0.0.1/32", "10.0.0.0/8"],
            "retention_note": "test",
        },
        "scrape_token": "test-scrape-token-abc",
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prometheus"]["enabled"] is True
    assert body["prometheus"]["has_scrape_token"] is True
    assert body["accepted_by"] == "test-owner"


@pytest.mark.asyncio
async def test_put_export_policy_rejects_invalid_cidr(migrated_client):
    payload = {
        "prometheus": {
            "enabled": True,
            "scrape_token_hash": "abc",
            "allowed_source_cidrs": ["not-a-cidr"],
            "retention_note": "",
        }
    }
    # The REST layer expects a scrape_token in the request to enable
    # Prometheus; the payload above omits it, so the request is
    # rejected as bad input. We rebuild the request to test the
    # cidr validator path through the domain directly.
    from livelead.domain.metrics_export.models import (
        OtelConfig,
        PrometheusConfig,
        SentryConfig,
        validate_policy_payload,
    )
    bad = PrometheusConfig(
        enabled=True,
        scrape_token_hash="abc",
        allowed_source_cidrs=("not-a-cidr",),
    )
    with pytest.raises(ValueError) as exc:
        validate_policy_payload(
            prometheus=bad, otel=OtelConfig(), sentry=SentryConfig()
        )
    assert "prometheus_cidr_invalid" in str(exc.value)


@pytest.mark.asyncio
async def test_put_export_policy_rejects_otel_sampling_ratio_out_of_range(migrated_client):
    payload = {
        "otel": {
            "enabled": True,
            "endpoint": "https://otel.example.com",
            "protocol": "http/protobuf",
            "sampling_ratio": 1.5,
            "redaction_header_keys": ["authorization"],
        },
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "otel_sampling_ratio_out_of_range" in r.json()["detail"]


@pytest.mark.asyncio
async def test_put_export_policy_enables_otel_with_acceptance(migrated_client):
    payload = {
        "otel": {
            "enabled": True,
            "endpoint": "https://otel.example.com",
            "protocol": "http/protobuf",
            "sampling_ratio": 0.1,
            "redaction_header_keys": ["authorization", "cookie"],
        },
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["otel"]["enabled"] is True
    assert body["otel"]["endpoint"] == "https://otel.example.com"
    assert body["otel"]["sampling_ratio"] == 0.1


@pytest.mark.asyncio
async def test_put_export_policy_rejects_sentry_without_dsn_ref(migrated_client):
    payload = {
        "sentry": {
            "enabled": True,
            "environment": "pilot_live",
            "sample_rate": 0.2,
        },
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "sentry_dsn_ref_required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_test_export_policy_returns_results_for_each_sink(migrated_client):
    r = await migrated_client.post(
        "/admin/observability/export-policy/test",
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "results" in body
    # Every sink should be present in the result map, even
    # when disabled; the status reflects the configuration.
    assert "prometheus_exposition" in body["results"]
    assert "otel_collector" in body["results"]
    assert "sentry_ingest" in body["results"]


@pytest.mark.asyncio
async def test_test_export_policy_forbidden_for_analyst(migrated_client):
    r = await migrated_client.post(
        "/admin/observability/export-policy/test",
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_disabled_without_policy(migrated_client):
    """A default-policy workspace returns 404 on /metrics because the sink is disabled."""

    r = await migrated_client.get("/metrics")
    assert r.status_code == 404
    assert r.json()["detail"] == "METRICS_DISABLED"


@pytest.mark.asyncio
async def test_metrics_endpoint_source_not_allowed_when_enabled(migrated_client):
    """The endpoint refuses requests from a non-allowlisted source."""

    # Enable Prometheus with a CIDR allowlist that does NOT
    # include the test client (the test transport uses
    # 127.0.0.1 as the client host).
    payload = {
        "prometheus": {
            "enabled": True,
            "allowed_source_cidrs": ["10.0.0.0/8"],
            "retention_note": "test",
        },
        "scrape_token": "test-scrape-token-abc",
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    # The test client uses 127.0.0.1 which is NOT in the
    # 10.0.0.0/8 allowlist. The endpoint must reject the
    # request with 403.
    r2 = await migrated_client.get("/metrics")
    assert r2.status_code == 403
    assert r2.json()["detail"] == "METRICS_SOURCE_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_metrics_endpoint_requires_scrape_token(migrated_client, monkeypatch):
    """The endpoint returns 401 when the scrape token is missing or wrong."""

    payload = {
        "prometheus": {
            "enabled": True,
            "allowed_source_cidrs": ["0.0.0.0/0"],
            "retention_note": "test",
        },
        "scrape_token": "test-scrape-token-abc",
        "accepted_by": "test-owner",
    }
    r = await migrated_client.put(
        "/admin/observability/export-policy",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    # With CIDR 0.0.0.0/0 the source check passes; the
    # request must be rejected because the token is missing.
    r2 = await migrated_client.get("/metrics")
    assert r2.status_code == 401
    assert r2.json()["detail"] == "METRICS_SCRAPE_TOKEN_INVALID"
