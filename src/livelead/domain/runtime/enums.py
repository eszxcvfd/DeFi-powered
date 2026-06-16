"""Runtime and live-cutover domain enums (US-040).

Pure enums only — no I/O. The mode vocabulary and live-integration names
match `docs/decisions/0018-pilot-live-cutover-baseline.md`.
"""

from __future__ import annotations

from enum import StrEnum


class EnvironmentMode(StrEnum):
    """Runtime environment profile state.

    The mode is read from the `LIVELEAD_ENVIRONMENT_MODE` setting and may be
    promoted or demoted at runtime through the cutover API.
    """

    TEST_LIKE = "test_like"
    PILOT_LIVE = "pilot_live"
    PAUSED = "paused"


class LiveIntegration(StrEnum):
    """Live integration toggle names.

    `discovery` controls whether real (non-mock) discovery connectors run.
    `ai_copilot` controls whether the live AI provider (Gemini) is used.
    `notifications` controls whether the live notification delivery path is
    active.
    `browser_external` controls whether supervised browser sessions can take
    real external actions.
    """

    DISCOVERY = "discovery"
    AI_COPILOT = "ai_copilot"
    NOTIFICATIONS = "notifications"
    BROWSER_EXTERNAL = "browser_external"


class LiveToggleState(StrEnum):
    """Explicit live-integration toggle states (US-040)."""

    DISABLED = "disabled"
    ENABLED = "enabled"


class LaunchGateSeverity(StrEnum):
    """Severity of a single launch-gate check."""

    OK = "ok"
    WARNING = "warning"
    BLOCKING = "blocking"


class BackupVerificationStatus(StrEnum):
    """Backup snapshot verification lifecycle (US-040)."""

    RECORDED = "recorded"
    VERIFIED_RESTORE = "verified_restore"
    FAILED_RESTORE = "failed_restore"


class CutoverAction(StrEnum):
    """Cutover event actions recorded in `cutover_events` (US-040)."""

    ENTER_PILOT_LIVE = "enter_pilot_live"
    PAUSE = "pause"
    ROLLBACK = "rollback"


class BackupFreshness(StrEnum):
    """Classification of a backup snapshot relative to launch-gate age."""

    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
