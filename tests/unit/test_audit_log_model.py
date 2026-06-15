"""Audit-log domain model and redaction rules (US-026)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import (
    AuditActor,
    AuditContext,
    AuditTarget,
    action_family,
    normalize_entry,
)
from livelead.domain.audit.redaction import (
    REDACTED,
    enforce_size_cap,
    is_sensitive_key,
    is_sensitive_value,
    redact_metadata,
    total_size,
)


def _actor() -> AuditActor:
    return AuditActor(actor_id="admin", actor_type=AuditActorType.HUMAN, role="admin")


def _target(tid: str = "src-1") -> AuditTarget:
    return AuditTarget(target_type=AuditTargetType.SOURCE, target_id=tid, display=tid)


def _ctx() -> AuditContext:
    return AuditContext(request_id="req-1", session_id="sess-1", ip="10.0.0.1", user_agent="e2e")


def test_action_family_extracts_first_segment():
    assert action_family(AuditAction.CONTENT_APPROVED) == "content"
    assert action_family(AuditAction.CLOAKBROWSER_KILL_SWITCH) == "cloakbrowser"
    assert action_family("auth.login.failed") == "auth"
    assert action_family("loose") == "loose"


def test_actor_validates_required_fields():
    with pytest.raises(ValueError):
        AuditActor(actor_id="", actor_type=AuditActorType.HUMAN, role="admin")
    with pytest.raises(ValueError):
        AuditActor(actor_id="x", actor_type="not-an-enum", role="x")  # type: ignore[arg-type]


def test_target_validates_required_fields():
    with pytest.raises(ValueError):
        AuditTarget(target_type=AuditTargetType.SOURCE, target_id="", display="x")
    with pytest.raises(ValueError):
        AuditTarget(target_type="bogus", target_id="x", display="x")  # type: ignore[arg-type]


def test_normalize_entry_redacts_known_sensitive_keys():
    entry = normalize_entry(
        organization_id=uuid4(),
        actor=_actor(),
        action=AuditAction.SOURCE_POLICY_CHANGED,
        target=_target(),
        outcome=AuditOutcome.SUCCEEDED,
        context=_ctx(),
        metadata={"api_key": "sk-test-1234567890ABCDEF", "note": "harmless"},
    )
    assert entry.metadata["api_key"] == REDACTED
    assert entry.metadata["note"] == "harmless"
    assert entry.metadata_redacted is True


def test_normalize_entry_redacts_secret_like_values():
    entry = normalize_entry(
        organization_id=uuid4(),
        actor=_actor(),
        action=AuditAction.SOURCE_POLICY_CHANGED,
        target=_target(),
        outcome=AuditOutcome.SUCCEEDED,
        context=_ctx(),
        metadata={"X-Custom-Header": "Bearer abcdefghijklmnop"},
    )
    assert entry.metadata["X-Custom-Header"] == REDACTED


def test_normalize_entry_truncates_oversized_strings():
    long = "x" * 1024
    entry = normalize_entry(
        organization_id=uuid4(),
        actor=_actor(),
        action=AuditAction.SOURCE_POLICY_CHANGED,
        target=_target(),
        outcome=AuditOutcome.SUCCEEDED,
        context=_ctx(),
        metadata={"body": long},
    )
    assert len(entry.metadata["body"]) <= 241
    assert entry.metadata_redacted is False


def test_normalize_entry_enforces_size_cap_on_huge_payloads():
    payload = {f"k{i}": "x" * 200 for i in range(400)}
    entry = normalize_entry(
        organization_id=uuid4(),
        actor=_actor(),
        action=AuditAction.SOURCE_POLICY_CHANGED,
        target=_target(),
        outcome=AuditOutcome.SUCCEEDED,
        context=_ctx(),
        metadata=payload,
    )
    assert entry.metadata.get("truncated") is True
    assert entry.metadata_redacted is True


def test_normalize_entry_serializes_to_json():
    entry = normalize_entry(
        organization_id=uuid4(),
        actor=_actor(),
        action=AuditAction.CONTENT_APPROVED,
        target=_target("draft-1"),
        outcome=AuditOutcome.DENIED,
        context=_ctx(),
        metadata={"event_id": "ev-1", "actor": "reviewer"},
    )
    payload = entry.to_dict()
    # Must round-trip through JSON to prove the schema is safe to persist.
    json.dumps(payload)
    assert payload["action_family"] == "content"
    assert payload["actor"]["actor_id"] == "admin"
    assert payload["target"]["target_id"] == "draft-1"


def test_redact_metadata_handles_nested_structures():
    cleaned = redact_metadata(
        {
            "a": {"api_key": "plain", "safe": 1},
            "b": [{"token": "abc"}, {"ok": "fine"}],
        }
    )
    assert cleaned["a"]["api_key"] == REDACTED
    assert cleaned["a"]["safe"] == 1
    assert cleaned["b"][0]["token"] == REDACTED
    assert cleaned["b"][1]["ok"] == "fine"


def test_is_sensitive_key_matches_known_names():
    assert is_sensitive_key("authorization")
    assert is_sensitive_key("API-KEY")
    assert is_sensitive_key("Session_Cookie")
    assert is_sensitive_key("password")
    assert not is_sensitive_key("event_id")
    assert not is_sensitive_key("")


def test_is_sensitive_value_matches_known_patterns():
    assert is_sensitive_value("Bearer abcdefghijklmnop")
    assert is_sensitive_value("sk-test-1234567890ABCDEF")
    assert is_sensitive_value("0123456789abcdef0123456789abcdef")
    assert not is_sensitive_value("alice@example.com")
    assert not is_sensitive_value("")


def test_enforce_size_cap_noop_when_small():
    value = {"k": "v"}
    assert enforce_size_cap(value) is value


def test_enforce_size_cap_replaces_when_oversized():
    huge = {f"k{i}": "x" * 200 for i in range(2000)}
    out = enforce_size_cap(huge)
    assert out.get("truncated") is True
    assert total_size(out) <= 8_192 + 200
