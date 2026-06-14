"""Read-only supervised browser actions (US-021)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class BrowserActionType(StrEnum):
    NAVIGATE = "navigate"
    SCROLL = "scroll"
    OPEN_DETAIL = "open_detail"
    READ_TEXT = "read_text"
    SUBMIT_FORM = "submit_form"


READ_ONLY_ACTIONS: frozenset[BrowserActionType] = frozenset(
    {
        BrowserActionType.NAVIGATE,
        BrowserActionType.SCROLL,
        BrowserActionType.OPEN_DETAIL,
        BrowserActionType.READ_TEXT,
    }
)


class BrowserActionLifecycle(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NEEDS_USER_ACTION = "needs_user_action"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class BrowserActionRequest:
    action_type: BrowserActionType
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BrowserActionResult:
    action_id: str
    action_type: BrowserActionType
    lifecycle: BrowserActionLifecycle
    summary: str
    detail: str | None = None
    policy_reason: str | None = None
    current_url: str | None = None
    text_preview: str | None = None
