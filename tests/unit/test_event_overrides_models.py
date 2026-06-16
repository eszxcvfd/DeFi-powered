"""Unit tests for the event override domain helpers (US-031)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from livelead.domain.event_overrides.models import (
    ALLOWED_OVERRIDE_FIELDS,
    OverrideValueKind,
    format_override_value,
    is_allowed_override_field,
    parse_override_value,
    value_kind_for,
)


def test_allowed_field_set_is_stable():
    assert ALLOWED_OVERRIDE_FIELDS == frozenset(
        {
            "canonical_title",
            "description",
            "organizer",
            "region",
            "starts_at",
            "source_url",
        }
    )


def test_is_allowed_override_field_rejects_unknown():
    assert is_allowed_override_field("canonical_title") is True
    assert is_allowed_override_field("id") is False
    assert is_allowed_override_field("campaign_id") is False
    assert is_allowed_override_field("observed_at") is False
    assert is_allowed_override_field("discovery_job_id") is False


def test_value_kind_for_matches_field():
    assert value_kind_for("canonical_title") is OverrideValueKind.TEXT
    assert value_kind_for("description") is OverrideValueKind.TEXT
    assert value_kind_for("organizer") is OverrideValueKind.TEXT
    assert value_kind_for("region") is OverrideValueKind.TEXT
    assert value_kind_for("source_url") is OverrideValueKind.URL
    assert value_kind_for("starts_at") is OverrideValueKind.TIMESTAMP


def test_parse_override_value_text_strips_whitespace():
    assert parse_override_value("canonical_title", "  Hello  ") == "Hello"
    assert parse_override_value("region", "EU") == "EU"


def test_parse_override_value_text_rejects_non_string():
    with pytest.raises(ValueError):
        parse_override_value("canonical_title", 123)


def test_parse_override_value_url_requires_scheme():
    assert parse_override_value("source_url", "https://example.com/e") == "https://example.com/e"
    with pytest.raises(ValueError):
        parse_override_value("source_url", "example.com/e")
    with pytest.raises(ValueError):
        parse_override_value("source_url", "ftp://example.com/e")


def test_parse_override_value_timestamp_accepts_zulu():
    parsed = parse_override_value("starts_at", "2026-07-01T09:00:00Z")
    assert isinstance(parsed, str)
    # The parser normalizes the timestamp; we only assert that the
    # stored string is a parseable ISO-8601 with timezone info.
    datetime.fromisoformat(parsed.replace("Z", "+00:00"))


def test_parse_override_value_timestamp_accepts_naive():
    parsed = parse_override_value("starts_at", "2026-07-01T09:00:00")
    assert parsed is not None
    # The parser interprets naive timestamps in the local timezone;
    # the round-trip stays parseable as ISO-8601.
    datetime.fromisoformat(parsed)


def test_parse_override_value_timestamp_rejects_garbage():
    with pytest.raises(ValueError):
        parse_override_value("starts_at", "not-a-date")


def test_parse_override_value_blank_returns_empty_string():
    assert parse_override_value("starts_at", "") == ""
    assert parse_override_value("starts_at", "   ") == ""
    assert parse_override_value("starts_at", None) == ""
    assert parse_override_value("canonical_title", "") == ""


def test_parse_override_value_rejects_unknown_field():
    with pytest.raises(ValueError):
        parse_override_value("campaign_id", "nope")


def test_format_override_value_round_trip_timestamp():
    original = "2026-07-01T09:00:00+00:00"
    stored = parse_override_value("starts_at", original)
    projected = format_override_value("starts_at", stored)
    assert isinstance(projected, datetime)
    assert projected.year == 2026 and projected.month == 7 and projected.day == 1


def test_format_override_value_blank_returns_none():
    assert format_override_value("canonical_title", "") is None
    assert format_override_value("starts_at", "") is None


def test_format_override_value_text_passthrough():
    assert format_override_value("canonical_title", "Hello") == "Hello"
