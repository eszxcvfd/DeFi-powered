"""Unit tests for the metric registry (US-042)."""

from __future__ import annotations

import pytest

from livelead.domain.metrics_export.models import (
    MetricDescriptor,
    MetricRegistry,
    MetricSample,
    exceeds_cardinality_budget,
)


def test_registry_default_mirrors_signal_provider_enum() -> None:
    """The default registry mirrors the closed `SignalProvider` enum from US-041
    and the closed `AlertMetric` enum extension from US-044.

    The first slice ships thirteen metrics: the six from US-041
    plus the two histograms the exporter uses for self-observability
    plus the five performance metrics from US-044.
    """

    registry = MetricRegistry()
    names = sorted(registry.supported_metrics())
    assert names == sorted(
        [
            "audit.retention_breach_risk",
            "backup.age_hours",
            "browser.crash_loop",
            "connector.failure_rate",
            "discovery.needs_user_action_rate",
            "worker.heartbeat.age_seconds",
            "alert.evaluator.duration_ms",
            "metrics.exporter.duration_ms",
            "api.read.latency_ms",
            "event.list.pagination.latency_ms",
            "discovery.first_progress_ms",
            "concurrency.users",
            "browser.session.budget_pct",
        ]
    )


def test_registry_refuses_duplicate_descriptors() -> None:
    """The constructor refuses to register the same metric twice."""

    descriptors = (
        MetricDescriptor(
            name="backup.age_hours",
            unit="hours",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="x",
        ),
        MetricDescriptor(
            name="backup.age_hours",
            unit="hours",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="y",
        ),
    )
    with pytest.raises(ValueError) as exc:
        MetricRegistry(descriptors=descriptors)
    assert "METRIC_REGISTRY_INVALID:duplicate_descriptor" in str(exc.value)


def test_registry_refuses_forbidden_metric() -> None:
    """A metric marked `forbidden` cannot be registered."""

    descriptors = (
        MetricDescriptor(
            name="some.private",
            unit="bytes",
            type="gauge",
            cardinality_budget=1,
            secret_safety="forbidden",
            description="x",
        ),
    )
    with pytest.raises(ValueError) as exc:
        MetricRegistry(descriptors=descriptors)
    assert "METRIC_REGISTRY_INVALID:forbidden_metric" in str(exc.value)


def test_registry_refuses_non_positive_cardinality() -> None:
    descriptors = (
        MetricDescriptor(
            name="backup.age_hours",
            unit="hours",
            type="gauge",
            cardinality_budget=0,
            secret_safety="safe",
            description="x",
        ),
    )
    with pytest.raises(ValueError) as exc:
        MetricRegistry(descriptors=descriptors)
    assert "METRIC_REGISTRY_INVALID:cardinality_non_positive" in str(exc.value)


def test_registry_filters_descriptors_not_in_allowed_metrics() -> None:
    """A metric not in the closed enum is filtered out by the constructor."""

    descriptors = (
        MetricDescriptor(
            name="backup.age_hours",
            unit="hours",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="x",
        ),
        MetricDescriptor(
            name="not.in.enum",
            unit="count",
            type="gauge",
            cardinality_budget=1,
            secret_safety="safe",
            description="y",
        ),
    )
    registry = MetricRegistry(
        descriptors=descriptors,
        allowed_metrics={"backup.age_hours"},
    )
    assert registry.is_registered("backup.age_hours")
    assert not registry.is_registered("not.in.enum")


def test_exceeds_cardinality_budget() -> None:
    desc = MetricDescriptor(
        name="connector.failure_rate",
        unit="ratio",
        type="gauge",
        cardinality_budget=2,
        secret_safety="safe",
        description="x",
    )
    ok_sample = MetricSample(
        name="connector.failure_rate",
        value=0.1,
        labels={"a": "1", "b": "2"},
    )
    too_many = MetricSample(
        name="connector.failure_rate",
        value=0.1,
        labels={"a": "1", "b": "2", "c": "3"},
    )
    assert not exceeds_cardinality_budget(ok_sample, desc)
    assert exceeds_cardinality_budget(too_many, desc)


def test_registry_get_returns_descriptor() -> None:
    registry = MetricRegistry()
    desc = registry.get("backup.age_hours")
    assert desc is not None
    assert desc.unit == "hours"
    assert desc.type == "gauge"
    assert desc.cardinality_budget == 1
    assert desc.secret_safety == "safe"
