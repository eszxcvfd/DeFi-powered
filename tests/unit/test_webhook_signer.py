"""Tests for the webhook signer (US-049)."""

from __future__ import annotations

import time

from livelead.application.webhooks.signer import (
    ID_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    build_request_body,
    compute_payload_hash,
    sign,
    verify,
)
from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)


def test_sign_returns_bounded_headers() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    headers = sign(
        body=body,
        secret="test-secret",
        timestamp=1700000000,
        delivery_id="del_01",
    )
    assert headers[ID_HEADER] == "del_01"
    assert headers[TIMESTAMP_HEADER] == "1700000000"
    assert headers[SIGNATURE_HEADER].startswith("v1,")
    assert len(headers[SIGNATURE_HEADER]) > 5


def test_sign_rejects_empty_secret() -> None:
    body = build_request_body({"a": 1})
    try:
        sign(
            body=body,
            secret="",
            timestamp=1700000000,
            delivery_id="del_01",
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_sign_rejects_empty_delivery_id() -> None:
    body = build_request_body({"a": 1})
    try:
        sign(
            body=body,
            secret="test-secret",
            timestamp=1700000000,
            delivery_id="",
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_verify_round_trip_succeeds() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    secret = "test-secret"
    timestamp = int(time.time())
    headers = sign(
        body=body,
        secret=secret,
        timestamp=timestamp,
        delivery_id="del_01",
    )
    assert (
        verify(
            body=body,
            secret=secret,
            timestamp_header=headers[TIMESTAMP_HEADER],
            signature_header=headers[SIGNATURE_HEADER],
            delivery_id_header=headers[ID_HEADER],
            now=timestamp,
        )
        is True
    )


def test_verify_rejects_tampered_body() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    secret = "test-secret"
    timestamp = int(time.time())
    headers = sign(
        body=body,
        secret=secret,
        timestamp=timestamp,
        delivery_id="del_01",
    )
    tampered = build_request_body({"a": 1, "b": "tampered"})
    assert (
        verify(
            body=tampered,
            secret=secret,
            timestamp_header=headers[TIMESTAMP_HEADER],
            signature_header=headers[SIGNATURE_HEADER],
            delivery_id_header=headers[ID_HEADER],
            now=timestamp,
        )
        is False
    )


def test_verify_rejects_tampered_secret() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    timestamp = int(time.time())
    headers = sign(
        body=body,
        secret="test-secret",
        timestamp=timestamp,
        delivery_id="del_01",
    )
    assert (
        verify(
            body=body,
            secret="tampered-secret",
            timestamp_header=headers[TIMESTAMP_HEADER],
            signature_header=headers[SIGNATURE_HEADER],
            delivery_id_header=headers[ID_HEADER],
            now=timestamp,
        )
        is False
    )


def test_verify_rejects_outside_replay_window() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    secret = "test-secret"
    timestamp = int(time.time())
    headers = sign(
        body=body,
        secret=secret,
        timestamp=timestamp,
        delivery_id="del_01",
    )
    # Now is far in the future.
    future = timestamp + WebhookDeliveryThresholds().signature_replay_window_seconds + 10
    assert (
        verify(
            body=body,
            secret=secret,
            timestamp_header=headers[TIMESTAMP_HEADER],
            signature_header=headers[SIGNATURE_HEADER],
            delivery_id_header=headers[ID_HEADER],
            now=future,
        )
        is False
    )


def test_verify_rejects_missing_signature() -> None:
    body = build_request_body({"a": 1})
    assert (
        verify(
            body=body,
            secret="test-secret",
            timestamp_header="1700000000",
            signature_header="",
            delivery_id_header="del_01",
        )
        is False
    )


def test_verify_rejects_missing_timestamp() -> None:
    body = build_request_body({"a": 1})
    assert (
        verify(
            body=body,
            secret="test-secret",
            timestamp_header="",
            signature_header="v1,abc",
            delivery_id_header="del_01",
        )
        is False
    )


def test_verify_rejects_wrong_signature_version() -> None:
    body = build_request_body({"a": 1})
    timestamp = int(time.time())
    assert (
        verify(
            body=body,
            secret="test-secret",
            timestamp_header=str(timestamp),
            signature_header="v2,abc",
            delivery_id_header="del_01",
            now=timestamp,
        )
        is False
    )


def test_compute_payload_hash_is_deterministic() -> None:
    body = build_request_body({"a": 1, "b": "two"})
    h1 = compute_payload_hash(body)
    h2 = compute_payload_hash(body)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_payload_hash_changes_with_body() -> None:
    h1 = compute_payload_hash(build_request_body({"a": 1}))
    h2 = compute_payload_hash(build_request_body({"a": 2}))
    assert h1 != h2


def test_build_request_body_is_stable() -> None:
    body1 = build_request_body({"b": 2, "a": 1})
    body2 = build_request_body({"a": 1, "b": 2})
    assert body1 == body2
    # No extra whitespace.
    assert b" " not in body1
