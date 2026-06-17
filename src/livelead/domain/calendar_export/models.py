"""Event calendar export domain models (US-045).

Pure dataclasses with no I/O. The infrastructure
layer is responsible for translating these to and
from SQLAlchemy rows. The model layer deliberately
does not import SQLAlchemy, FastAPI, or any
framework.

The model layer reuses the closed `CalendarScope`,
`CalendarExportResult`, and `CalendarTimeState`
enums from `livelead.domain.calendar_export.enums`
and the closed token TTL bound from the
`EnvironmentMode` shipped by `US-040`. The
`CalendarExportService` is the only place that
mutates `calendar_export_tokens` and
`calendar_export_audits`; the REST layer calls it
from the request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.calendar_export.enums import (
    CalendarExportResult,
    CalendarScope,
    CalendarTimeState,
)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalendarExportToken:
    """A durable bounded calendar export token.

    The row carries enough information to mint, resolve,
    revoke, and audit a tokenized ICS feed without
    leaking the plaintext token or any session-bound
    material. The `token_hash` is the only durable
    artifact; the plaintext is never stored.
    """

    id: str
    organization_id: str
    user_id: str
    token_hash: str
    scope: CalendarScope
    target_id: str | None
    filter_json: dict[str, Any] | None
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    use_count: int = 0
    audit_correlation_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_active(self, *, now: datetime | None = None) -> bool:
        """Return True when the token is not revoked and not expired."""

        if self.revoked_at is not None:
            return False
        reference = now or datetime.utcnow()
        if self.expires_at <= reference:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "scope": self.scope.value,
            "target_id": self.target_id,
            "filter_json": self.filter_json,
            "expires_at": (
                self.expires_at.isoformat() if self.expires_at else None
            ),
            "revoked_at": (
                self.revoked_at.isoformat() if self.revoked_at else None
            ),
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "use_count": int(self.use_count),
            "audit_correlation_id": self.audit_correlation_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalendarExportAudit:
    """A durable record of every calendar export attempt.

    The row is the audit-of-record for the calendar
    export surface and is consumed by the operator
    panel widget and the existing admin audit log
    filter from `US-026`. The row stores a redacted
    IP address, a bounded user agent, and a request
    id; the secret-safe payload contract from
    `US-041` is enforced before persistence.
    """

    id: str
    organization_id: str
    user_id: str | None
    token_id: str | None
    scope: CalendarScope
    event_id: str | None
    event_count: int
    result: CalendarExportResult
    ip_address: str
    user_agent: str
    request_id: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "token_id": self.token_id,
            "scope": self.scope.value,
            "event_id": self.event_id,
            "event_count": int(self.event_count),
            "result": self.result.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Filter shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalendarExportFilter:
    """The closed filter shape for `event_filter` exports.

    The filter is bounded so the calendar export
    surface cannot be repurposed to query arbitrary
    data. New fields cannot be added without first
    extending the `CalendarExportService` and the
    audit entry shape.
    """

    campaign_id: str | None = None
    industry: str | None = None
    region: str | None = None
    label: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "industry": self.industry,
            "region": self.region,
            "label": self.label,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any] | None) -> "CalendarExportFilter":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            campaign_id=_opt_str(payload.get("campaign_id")),
            industry=_opt_str(payload.get("industry")),
            region=_opt_str(payload.get("region")),
            label=str(payload.get("label") or "")[:64],
        )

    def label_text(self) -> str:
        if self.label:
            return self.label
        parts: list[str] = []
        if self.campaign_id:
            parts.append(f"campaign={self.campaign_id}")
        if self.industry:
            parts.append(f"industry={self.industry}")
        if self.region:
            parts.append(f"region={self.region}")
        return ", ".join(parts) or "default"


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


# ---------------------------------------------------------------------------
# Time state classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EventTimeStateView:
    """A per-event time state classification result.

    The view is the only place the bounded path
    exposes a per-event time state to the formatter.
    The view carries the source `starts_at` and
    `ended_at` timestamps so a future story can
    extend the classification without redefining
    the surface.
    """

    event_id: str
    time_state: CalendarTimeState
    starts_at: datetime | None
    ended_at: datetime | None


__all__ = [
    "CalendarExportAudit",
    "CalendarExportFilter",
    "CalendarExportToken",
    "EventTimeStateView",
]
