"""Unit tests for the metrics export service (US-042)."""

from __future__ import annotations

import hashlib
import hmac
import os

import pytest

from livelead.application.metrics_export.service import (
    ExportPolicyAcceptanceRequired,
    ExportPolicyValidationError,
    MetricsExportService,
    _hash_scrape_token,
    verify_scrape_token,
)
from livelead.domain.metrics_export.enums import ExportStatus, MetricsSink
from livelead.domain.metrics_export.models import (
    MetricsExportPolicy,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
)


def test_hash_scrape_token_is_deterministic() -> None:
    salt = "test-salt"
    os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"] = salt
    try:
        h1 = _hash_scrape_token("token-abc")
        h2 = _hash_scrape_token("token-abc")
        assert h1 == h2
        # Different token must produce a different hash.
        assert _hash_scrape_token("token-xyz") != h1
    finally:
        del os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"]


def test_verify_scrape_token_accepts_correct_token() -> None:
    salt = "test-salt"
    os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"] = salt
    try:
        token = "token-abc"
        stored = _hash_scrape_token(token)
        assert verify_scrape_token(token, stored) is True
    finally:
        del os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"]


def test_verify_scrape_token_rejects_wrong_token() -> None:
    salt = "test-salt"
    os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"] = salt
    try:
        stored = _hash_scrape_token("token-abc")
        assert verify_scrape_token("token-xyz", stored) is False
    finally:
        del os.environ["LIVELEAD_PROMETHEUS_SCRAPE_SALT"]


def test_verify_scrape_token_rejects_empty_stored_hash() -> None:
    assert verify_scrape_token("token-abc", "") is False
