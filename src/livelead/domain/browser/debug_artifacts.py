"""Browser debug artifacts — gating, retention, redaction (US-023)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from livelead.domain.browser.models import BrowserSessionState

DEFAULT_SCREENSHOT_RETENTION_DAYS = 14
DEFAULT_CONSOLE_LOG_RETENTION_DAYS = 7
DEFAULT_TRACE_RETENTION_DAYS = 7

SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|secret|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+"),
    re.compile(r"(?i)cookie\s*[:=]\s*[^;\n]+"),
    re.compile(r"(?i)set-cookie\s*:\s*[^\n]+"),
)


class BrowserArtifactType(StrEnum):
    SCREENSHOT = "screenshot"
    CONSOLE_LOG = "console_log"
    TRACE = "trace"


class BrowserArtifactStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrowserArtifactCaptureMode(StrEnum):
    MANUAL = "manual"
    DEBUG_AUTO = "debug_auto"
    FAILURE = "failure"


SCREENSHOT_ELIGIBLE_STATES = frozenset(
    {
        BrowserSessionState.RUNNING,
        BrowserSessionState.NEEDS_USER_ACTION,
        BrowserSessionState.STOPPED,
        BrowserSessionState.COMPLETED,
    }
)


def parse_browser_artifact_policy(rate_limit_json: str | None) -> dict:
    if not rate_limit_json:
        return {
            "screenshots_allowed": True,
            "debug_capture_allowed": True,
            "screenshot_retention_days": DEFAULT_SCREENSHOT_RETENTION_DAYS,
        }
    try:
        data = json.loads(rate_limit_json)
    except json.JSONDecodeError:
        return {
            "screenshots_allowed": True,
            "debug_capture_allowed": True,
            "screenshot_retention_days": DEFAULT_SCREENSHOT_RETENTION_DAYS,
        }
    if not isinstance(data, dict):
        return {
            "screenshots_allowed": True,
            "debug_capture_allowed": True,
            "screenshot_retention_days": DEFAULT_SCREENSHOT_RETENTION_DAYS,
        }
    return {
        "screenshots_allowed": data.get("browser_screenshots_allowed", True) is not False,
        "debug_capture_allowed": data.get("browser_debug_capture_allowed", True) is not False,
        "screenshot_retention_days": _clamp_days(
            data.get("browser_screenshot_retention_days"), DEFAULT_SCREENSHOT_RETENTION_DAYS
        ),
        "console_log_retention_days": _clamp_days(
            data.get("browser_console_log_retention_days"), DEFAULT_CONSOLE_LOG_RETENTION_DAYS
        ),
        "trace_retention_days": _clamp_days(
            data.get("browser_trace_retention_days"), DEFAULT_TRACE_RETENTION_DAYS
        ),
    }


def _clamp_days(raw: object, default: int) -> int:
    try:
        n = int(raw)  # type: ignore[arg-type]
        return max(1, min(90, n))
    except (TypeError, ValueError):
        return default


def retention_expires_at(
    *,
    artifact_type: BrowserArtifactType,
    policy: dict,
    now: datetime | None = None,
) -> datetime:
    base = now or datetime.now(UTC)
    if artifact_type == BrowserArtifactType.SCREENSHOT:
        days = int(
            policy.get("screenshot_retention_days")
            or policy.get("browser_screenshot_retention_days")
            or DEFAULT_SCREENSHOT_RETENTION_DAYS
        )
    elif artifact_type == BrowserArtifactType.CONSOLE_LOG:
        days = int(policy.get("console_log_retention_days", DEFAULT_CONSOLE_LOG_RETENTION_DAYS))
    else:
        days = int(policy.get("trace_retention_days", DEFAULT_TRACE_RETENTION_DAYS))
    return base + timedelta(days=days)


def effective_artifact_status(
    stored: BrowserArtifactStatus,
    *,
    expires_at: datetime,
    now: datetime | None = None,
) -> BrowserArtifactStatus:
    if stored != BrowserArtifactStatus.ACTIVE:
        return stored
    base = now or datetime.now(UTC)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    if base >= exp:
        return BrowserArtifactStatus.EXPIRED
    return stored


def sanitize_text_payload(text: str) -> tuple[str, bool]:
    """Returns (sanitized, was_redacted)."""
    out = text
    redacted = False
    for pat in SECRET_PATTERNS:
        if pat.search(out):
            out = pat.sub("[REDACTED]", out)
            redacted = True
    if "eyJ" in out and len(out) > 40:
        out = re.sub(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", out)
        redacted = True
    return out, redacted


def block_unsafe_binary_payload(data: bytes) -> bool:
    """True if payload should be blocked (cookie jar markers, etc.)."""
    sample = data[:4096].lower()
    if b"set-cookie:" in sample or b"__secure-" in sample:
        return True
    return False


@dataclass(frozen=True, slots=True)
class CaptureDecision:
    allowed: bool
    reason: str | None = None


def can_capture_screenshot(
    *,
    session_state: BrowserSessionState,
    policy: dict,
) -> CaptureDecision:
    if not policy.get("screenshots_allowed", True):
        return CaptureDecision(False, "screenshots_not_allowed")
    if session_state not in SCREENSHOT_ELIGIBLE_STATES:
        return CaptureDecision(False, "session_not_eligible_for_screenshot")
    return CaptureDecision(True, None)


def can_enable_debug(*, policy: dict, actor_role: str) -> CaptureDecision:
    if actor_role not in ("analyst", "admin", "owner"):
        return CaptureDecision(False, "role_cannot_enable_debug")
    if not policy.get("debug_capture_allowed", True):
        return CaptureDecision(False, "debug_capture_not_allowed")
    return CaptureDecision(True, None)


def can_access_artifact(
    *,
    status: BrowserArtifactStatus,
    expires_at: datetime,
    organization_id: str,
    artifact_org_id: str,
    actor_role: str,
) -> CaptureDecision:
    if organization_id != artifact_org_id:
        return CaptureDecision(False, "cross_tenant")
    if actor_role not in ("analyst", "admin", "owner"):
        return CaptureDecision(False, "role_cannot_access_artifact")
    effective = effective_artifact_status(status, expires_at=expires_at)
    if effective == BrowserArtifactStatus.EXPIRED:
        return CaptureDecision(False, "artifact_expired")
    if effective != BrowserArtifactStatus.ACTIVE:
        return CaptureDecision(False, f"artifact_{effective.value}")
    return CaptureDecision(True, None)