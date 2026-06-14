"""Confirmation-gated browser actions (US-022)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserSessionState

DEFAULT_CONFIRMATION_TTL_SECONDS = 900


class ConfirmationGatedActionType(StrEnum):
    SUBMIT_FORM = "submit_form"


CONFIRMATION_GATED_ACTIONS: frozenset[BrowserActionType] = frozenset({BrowserActionType.SUBMIT_FORM})


class BrowserConfirmationState(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    EXECUTED = "executed"
    BLOCKED = "blocked"


TERMINAL_CONFIRMATION_STATES = frozenset(
    {
        BrowserConfirmationState.CANCELLED,
        BrowserConfirmationState.EXPIRED,
        BrowserConfirmationState.EXECUTED,
        BrowserConfirmationState.BLOCKED,
    }
)


def requires_confirmation(action_type: BrowserActionType) -> bool:
    return action_type in CONFIRMATION_GATED_ACTIONS


def parse_confirmation_gated_allowlist(rate_limit_json: str | None) -> frozenset[BrowserActionType]:
    import json

    if not rate_limit_json:
        return frozenset()
    try:
        data = json.loads(rate_limit_json)
    except json.JSONDecodeError:
        return frozenset()
    if not isinstance(data, dict):
        return frozenset()
    raw = data.get("browser_confirmation_gated_actions")
    if raw is None:
        return frozenset({BrowserActionType.SUBMIT_FORM})
    if isinstance(raw, list):
        out: set[BrowserActionType] = set()
        for item in raw:
            try:
                at = BrowserActionType(str(item).lower().strip())
                if requires_confirmation(at):
                    out.add(at)
            except ValueError:
                continue
        return frozenset(out)
    return frozenset({BrowserActionType.SUBMIT_FORM})


def normalize_submit_form_parameters(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    errors: list[str] = []
    form_id = str(raw.get("form_id") or raw.get("form") or "primary").strip()[:64] or "primary"
    intent = str(raw.get("intent") or "submit_form").strip()[:64]
    target_label = str(raw.get("target_label") or raw.get("label") or "").strip()[:200]
    params: dict[str, Any] = {
        "form_id": form_id,
        "intent": intent,
        "target_label": target_label or f"Form «{form_id}»",
    }
    if raw.get("dry_run_only"):
        params["dry_run_only"] = True
    return params, tuple(errors)


def build_action_preview(
    *,
    action_type: BrowserActionType,
    parameters: dict[str, Any],
    session_url: str,
    source_name: str,
) -> dict[str, Any]:
    if action_type == BrowserActionType.SUBMIT_FORM:
        label = str(parameters.get("target_label") or "form")
        return {
            "action_type": action_type.value,
            "title": "Submit form (dry-run preview)",
            "impact_summary": (
                f"This would submit «{label}» on the supervised page. "
                "No external submit runs until you confirm."
            ),
            "target_url": session_url,
            "source_name": source_name,
            "parameters_summary": {
                "form_id": parameters.get("form_id"),
                "intent": parameters.get("intent"),
            },
        }
    return {
        "action_type": action_type.value,
        "title": "Side-effect action",
        "impact_summary": "Confirmation required before execution.",
        "target_url": session_url,
        "source_name": source_name,
        "parameters_summary": parameters,
    }


def confirmation_expires_at(*, now: datetime | None = None, ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS) -> datetime:
    base = now or datetime.now(UTC)
    return base + timedelta(seconds=ttl_seconds)


def effective_confirmation_state(
    stored_state: BrowserConfirmationState,
    *,
    expires_at: datetime,
    now: datetime | None = None,
) -> BrowserConfirmationState:
    if stored_state != BrowserConfirmationState.PENDING:
        return stored_state
    base = now or datetime.now(UTC)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    if base >= exp:
        return BrowserConfirmationState.EXPIRED
    return stored_state


@dataclass(frozen=True, slots=True)
class ConfirmationDecision:
    allowed: bool
    state: BrowserConfirmationState
    reason: str | None = None


def can_confirm(
    *,
    state: BrowserConfirmationState,
    expires_at: datetime,
    session_state: BrowserSessionState,
    now: datetime | None = None,
) -> ConfirmationDecision:
    effective = effective_confirmation_state(state, expires_at=expires_at, now=now)
    if effective == BrowserConfirmationState.EXPIRED:
        return ConfirmationDecision(False, BrowserConfirmationState.EXPIRED, "confirmation_expired")
    if effective != BrowserConfirmationState.PENDING:
        return ConfirmationDecision(False, effective, "confirmation_not_pending")
    if session_state not in (
        BrowserSessionState.RUNNING,
        BrowserSessionState.NEEDS_USER_ACTION,
    ):
        return ConfirmationDecision(False, BrowserConfirmationState.BLOCKED, "session_not_actionable")
    return ConfirmationDecision(True, BrowserConfirmationState.PENDING, None)


def can_cancel(
    *,
    state: BrowserConfirmationState,
    expires_at: datetime,
    now: datetime | None = None,
) -> ConfirmationDecision:
    effective = effective_confirmation_state(state, expires_at=expires_at, now=now)
    if effective == BrowserConfirmationState.EXPIRED:
        return ConfirmationDecision(False, BrowserConfirmationState.EXPIRED, "confirmation_expired")
    if effective != BrowserConfirmationState.PENDING:
        return ConfirmationDecision(False, effective, "confirmation_not_pending")
    return ConfirmationDecision(True, BrowserConfirmationState.PENDING, None)