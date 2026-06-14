"""Allowlist, budget, and session eligibility for read-only browser actions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from livelead.domain.browser.action_confirmation import requires_confirmation
from livelead.domain.browser.actions import BrowserActionType, READ_ONLY_ACTIONS
from livelead.domain.browser.models import BrowserSessionState

DEFAULT_MAX_ACTIONS_PER_SESSION = 25
DEFAULT_ACTION_TIMEOUT_MS = 30_000

ACTION_ELIGIBLE_STATES = frozenset(
    {
        BrowserSessionState.RUNNING,
        BrowserSessionState.NEEDS_USER_ACTION,
    }
)


@dataclass(frozen=True, slots=True)
class ActionPolicyDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()


def parse_browser_action_allowlist(rate_limit_json: str | None) -> frozenset[BrowserActionType]:
    if not rate_limit_json:
        return frozenset(BrowserActionType)
    try:
        data = json.loads(rate_limit_json)
    except json.JSONDecodeError:
        return frozenset(BrowserActionType)
    if not isinstance(data, dict):
        return frozenset(BrowserActionType)
    raw = data.get("browser_read_only_actions")
    if raw is None:
        return frozenset(BrowserActionType)
    if isinstance(raw, list):
        out: set[BrowserActionType] = set()
        for item in raw:
            try:
                out.add(BrowserActionType(str(item).lower().strip()))
            except ValueError:
                continue
        return frozenset(out) if out else frozenset()
    return frozenset(BrowserActionType)


def max_actions_per_session(rate_limit_json: str | None) -> int:
    if not rate_limit_json:
        return DEFAULT_MAX_ACTIONS_PER_SESSION
    try:
        data = json.loads(rate_limit_json)
        if isinstance(data, dict) and isinstance(data.get("browser_action_budget"), int):
            n = int(data["browser_action_budget"])
            return max(1, min(200, n))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return DEFAULT_MAX_ACTIONS_PER_SESSION


def action_timeout_ms(rate_limit_json: str | None) -> int:
    if not rate_limit_json:
        return DEFAULT_ACTION_TIMEOUT_MS
    try:
        data = json.loads(rate_limit_json)
        if isinstance(data, dict) and isinstance(data.get("browser_action_timeout_ms"), int):
            n = int(data["browser_action_timeout_ms"])
            return max(5_000, min(120_000, n))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return DEFAULT_ACTION_TIMEOUT_MS


def evaluate_action_policy_with_json(
    *,
    allowlist: frozenset[BrowserActionType],
    session_state: BrowserSessionState,
    action_type: BrowserActionType,
    actions_used: int,
    max_actions: int,
) -> ActionPolicyDecision:
    reasons: list[str] = []
    if session_state not in ACTION_ELIGIBLE_STATES:
        reasons.append("session_not_actionable")
    if requires_confirmation(action_type):
        reasons.append("use_confirmation_flow")
    elif action_type not in READ_ONLY_ACTIONS:
        reasons.append("not_read_only_action")
    if action_type not in allowlist:
        reasons.append("action_not_allowlisted")
    if actions_used >= max_actions:
        reasons.append("action_budget_exceeded")
    if reasons:
        return ActionPolicyDecision(allowed=False, reasons=tuple(dict.fromkeys(reasons)))
    return ActionPolicyDecision(allowed=True)


def normalize_action_parameters(
    action_type: BrowserActionType, raw: dict[str, Any]
) -> tuple[dict[str, Any], tuple[str, ...]]:
    errors: list[str] = []
    params: dict[str, Any] = {}
    if action_type == BrowserActionType.NAVIGATE:
        url = str(raw.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            errors.append("invalid_navigate_url")
        else:
            params["url"] = url
    elif action_type == BrowserActionType.SCROLL:
        delta = raw.get("delta_y", 400)
        try:
            params["delta_y"] = max(-2000, min(2000, int(delta)))
        except (TypeError, ValueError):
            params["delta_y"] = 400
    elif action_type == BrowserActionType.OPEN_DETAIL:
        selector = str(raw.get("selector") or "").strip()
        role = str(raw.get("role") or "link").strip() or "link"
        name = str(raw.get("name") or "").strip()
        if selector:
            params["selector"] = selector[:500]
            params["locator_mode"] = "css_fallback"
        elif name:
            params["role"] = role[:32]
            params["name"] = name[:200]
            params["locator_mode"] = "semantic"
        else:
            params["role"] = "link"
            params["locator_mode"] = "semantic_first_link"
    elif action_type == BrowserActionType.READ_TEXT:
        selector = str(raw.get("selector") or "body").strip() or "body"
        params["selector"] = selector[:500]
        params["max_chars"] = min(8000, max(200, int(raw.get("max_chars", 2000) or 2000)))
    if errors:
        return {}, tuple(errors)
    return params, ()


def is_safe_navigate_url(url: str, *, source_domain: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return False
    if not host:
        return False
    sd = (source_domain or "").lower().removeprefix("www.")
    if not sd:
        return True
    return host == sd or host.endswith("." + sd) or sd.endswith("." + host)
