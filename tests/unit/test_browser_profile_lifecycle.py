from datetime import UTC, datetime, timedelta

from livelead.domain.browser.profiles import (
    BrowserProfileConsentStatus,
    BrowserProfileLifecycle,
    can_store_state_material,
    can_transition_delete,
    can_transition_lock,
    effective_lifecycle,
    evaluate_profile_launch,
    secret_safe_summary,
)


def test_effective_lifecycle_expired_by_timestamp():
    past = datetime.now(UTC) - timedelta(days=1)
    eff = effective_lifecycle(BrowserProfileLifecycle.ACTIVE, expires_at=past)
    assert eff == BrowserProfileLifecycle.EXPIRED


def test_launch_blocked_when_locked():
    elig = evaluate_profile_launch(
        lifecycle=BrowserProfileLifecycle.LOCKED,
        expires_at=None,
        consent_status=BrowserProfileConsentStatus.NONE,
        has_state_material=False,
    )
    assert not elig.eligible
    assert "profile_locked" in elig.reasons


def test_launch_requires_consent_when_state_present():
    elig = evaluate_profile_launch(
        lifecycle=BrowserProfileLifecycle.ACTIVE,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        consent_status=BrowserProfileConsentStatus.NONE,
        has_state_material=True,
    )
    assert not elig.eligible
    assert "profile_consent_required" in elig.reasons


def test_store_state_material_requires_consent():
    ok, reason = can_store_state_material(
        consent_status=BrowserProfileConsentStatus.NONE,
        lifecycle=BrowserProfileLifecycle.ACTIVE,
    )
    assert not ok
    assert reason == "consent_not_granted"


def test_secret_safe_summary_never_exposes_raw():
    s = secret_safe_summary(
        has_state_material=True,
        consent_status=BrowserProfileConsentStatus.GRANTED,
    )
    assert s["state_material_present"] is True
    assert s["raw_state_exposed"] is False


def test_lock_and_delete_transitions():
    assert can_transition_lock(BrowserProfileLifecycle.ACTIVE)
    assert not can_transition_lock(BrowserProfileLifecycle.LOCKED)
    assert can_transition_delete(BrowserProfileLifecycle.ACTIVE)
    assert not can_transition_delete(BrowserProfileLifecycle.DELETED)