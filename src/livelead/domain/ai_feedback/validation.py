"""AI feedback validation and no-auto-learning guardrails (US-038)."""

from __future__ import annotations

from livelead.domain.ai_feedback.models import (
    NOTE_MAX_LEN,
    AiFeedbackReasonCode,
    AiFeedbackTargetType,
    AudienceHypothesisFeedbackState,
    DiscoveryCopilotFeedbackState,
)

_AUTO_LEARNING_FORBIDDEN_ACTIONS = frozenset(
    {
        "mutate_scoring_weights",
        "mutate_prompt_template",
        "mutate_connector_selection",
        "regenerate_ai_output",
    }
)


def assert_no_auto_learning_side_effect(action: str) -> None:
    if action in _AUTO_LEARNING_FORBIDDEN_ACTIONS:
        raise ValueError("feedback must not trigger autonomous learning")


def validate_discovery_copilot_feedback(
    *,
    state: str,
    reason_code: str | None,
    note: str | None,
) -> tuple[str, str | None, str | None]:
    try:
        parsed = DiscoveryCopilotFeedbackState(state.strip().lower())
    except ValueError as exc:
        raise ValueError("unsupported discovery copilot feedback state") from exc
    reason = _normalize_reason(reason_code)
    text = _normalize_note(note)
    if parsed == DiscoveryCopilotFeedbackState.NOT_HELPFUL and not reason:
        raise ValueError("reason_code required for not_helpful feedback")
    return parsed.value, reason, text


def validate_audience_hypothesis_feedback(
    *,
    state: str,
    reason_code: str | None,
    note: str | None,
) -> tuple[str, str | None, str | None]:
    try:
        parsed = AudienceHypothesisFeedbackState(state.strip().lower())
    except ValueError as exc:
        raise ValueError("unsupported audience hypothesis feedback state") from exc
    reason = _normalize_reason(reason_code)
    text = _normalize_note(note)
    if parsed in (
        AudienceHypothesisFeedbackState.INCORRECT,
        AudienceHypothesisFeedbackState.UNCERTAIN,
    ) and not reason:
        raise ValueError("reason_code required for incorrect or uncertain feedback")
    return parsed.value, reason, text


def validate_target_type(value: str) -> AiFeedbackTargetType:
    try:
        return AiFeedbackTargetType(value.strip().lower())
    except ValueError as exc:
        raise ValueError("unsupported feedback target type") from exc


def _normalize_reason(reason_code: str | None) -> str | None:
    if reason_code is None or not str(reason_code).strip():
        return None
    raw = str(reason_code).strip().lower()
    try:
        return AiFeedbackReasonCode(raw).value
    except ValueError as exc:
        raise ValueError("unsupported reason_code") from exc


def _normalize_note(note: str | None) -> str | None:
    if note is None:
        return None
    text = str(note).strip()
    if not text:
        return None
    if len(text) > NOTE_MAX_LEN:
        raise ValueError(f"note must be at most {NOTE_MAX_LEN} characters")
    return text