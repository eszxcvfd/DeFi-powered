from datetime import UTC, datetime, timedelta

from livelead.domain.browser.action_confirmation import (
    BrowserConfirmationState,
    build_action_preview,
    can_cancel,
    can_confirm,
    confirmation_expires_at,
    effective_confirmation_state,
    normalize_submit_form_parameters,
    requires_confirmation,
)
from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserSessionState


def test_requires_confirmation_submit_form():
    assert requires_confirmation(BrowserActionType.SUBMIT_FORM) is True
    assert requires_confirmation(BrowserActionType.SCROLL) is False


def test_preview_aligns_with_parameters():
    params, errs = normalize_submit_form_parameters({"form_id": "signup", "target_label": "Register"})
    assert not errs
    preview = build_action_preview(
        action_type=BrowserActionType.SUBMIT_FORM,
        parameters=params,
        session_url="https://example.com/page",
        source_name="Example",
    )
    assert preview["parameters_summary"]["form_id"] == "signup"
    assert "Register" in preview["impact_summary"]


def test_expired_pending_cannot_confirm():
    exp = datetime.now(UTC) - timedelta(seconds=1)
    d = can_confirm(
        state=BrowserConfirmationState.PENDING,
        expires_at=exp,
        session_state=BrowserSessionState.RUNNING,
    )
    assert not d.allowed
    assert d.state == BrowserConfirmationState.EXPIRED


def test_cancel_idempotent_on_pending():
    exp = confirmation_expires_at()
    d = can_cancel(state=BrowserConfirmationState.PENDING, expires_at=exp)
    assert d.allowed


def test_effective_state_marks_expired():
    exp = datetime.now(UTC) - timedelta(minutes=1)
    assert (
        effective_confirmation_state(BrowserConfirmationState.PENDING, expires_at=exp)
        == BrowserConfirmationState.EXPIRED
    )