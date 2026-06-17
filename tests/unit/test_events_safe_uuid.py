"""Unit tests for the `_safe_uuid` helper in
`livelead.interfaces.rest.events`.

The pre-existing `events.discovery_job_id` column
carries free-form ids from US-004 manual
discovery (`manual-job-id` is a real fixture
value); the column is not constrained to UUIDs
at the SQL level. The list endpoints must return
`None` for malformed values rather than crash
with `ValueError: badly formed hexadecimal UUID
string`.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from livelead.interfaces.rest.events import _safe_uuid


def test_safe_uuid_returns_none_for_none() -> None:
    assert _safe_uuid(None) is None


def test_safe_uuid_returns_none_for_empty_string() -> None:
    assert _safe_uuid("") is None


def test_safe_uuid_parses_valid_uuid() -> None:
    value = str(uuid4())
    result = _safe_uuid(value)
    assert isinstance(result, UUID)
    assert str(result) == value


def test_safe_uuid_returns_none_for_manual_job_id() -> None:
    # Real fixture value from US-004 manual
    # discovery.
    assert _safe_uuid("manual-job-id") is None


def test_safe_uuid_returns_none_for_short_string() -> None:
    assert _safe_uuid("abc") is None


def test_safe_uuid_returns_none_for_non_uuid_string() -> None:
    assert _safe_uuid("not-a-uuid-at-all") is None


def test_safe_uuid_returns_none_for_partial_uuid() -> None:
    # Looks like a UUID prefix but is malformed.
    assert _safe_uuid("12345678-1234-1234-1234") is None


def test_safe_uuid_returns_none_for_integer() -> None:
    assert _safe_uuid(12345) is None  # type: ignore[arg-type]


def test_safe_uuid_returns_none_for_dict() -> None:
    assert _safe_uuid({"id": "x"}) is None  # type: ignore[arg-type]
