from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.cloakbrowser.policy import (
    CloakBrowserPolicySnapshot,
    CloakBrowserPolicyState,
    CloakBrowserRuntimePolicyInput,
    CloakBrowserRuntimeStatus,
    derive_policy_state,
    evaluate_cloakbrowser_launch,
    evaluate_runtime_policy,
)


def _snapshot(**kwargs) -> CloakBrowserPolicySnapshot:
    base = dict(
        source_id=uuid4(),
        organization_id=uuid4(),
        state=CloakBrowserPolicyState.APPROVED,
        purpose_rationale="partner portal",
        owner_admin_approved=True,
        compliance_approved=True,
        owner_admin_actor="admin",
        compliance_actor="compliance",
        owner_admin_approved_at=datetime.now(UTC),
        compliance_approved_at=datetime.now(UTC),
        revoked_at=None,
        revoked_by=None,
        revoke_reason=None,
        pinned_version="1.0.0",
        runtime_status=CloakBrowserRuntimeStatus.OK,
    )
    base.update(kwargs)
    return CloakBrowserPolicySnapshot(**base)


def test_kill_switch_overrides_approved_snapshot():
    snap = _snapshot()
    inp = CloakBrowserRuntimePolicyInput(kill_switch_active=True, pinned_version="1.0.0", runtime_version="1.0.0")
    allowed, reasons, status = evaluate_cloakbrowser_launch(
        automation_engine="cloakbrowser",
        snapshot=snap,
        runtime_input=inp,
    )
    assert not allowed
    assert "cloakbrowser_kill_switch" in reasons
    assert status == CloakBrowserRuntimeStatus.KILL_SWITCH


def test_checksum_mismatch_blocks_even_when_approved():
    snap = _snapshot(runtime_status=CloakBrowserRuntimeStatus.CHECKSUM_FAILED)
    inp = CloakBrowserRuntimePolicyInput(
        pinned_version="1.0.0",
        runtime_version="1.0.0",
        expected_checksum="abc",
        runtime_checksum="def",
    )
    allowed, reasons, _ = evaluate_cloakbrowser_launch(
        automation_engine="cloakbrowser",
        snapshot=snap,
        runtime_input=inp,
    )
    assert not allowed
    assert "cloakbrowser_runtime_policy_failed" in reasons


def test_playwright_engine_skips_cloak_gates():
    allowed, reasons, status = evaluate_cloakbrowser_launch(
        automation_engine="playwright",
        snapshot=None,
        runtime_input=CloakBrowserRuntimePolicyInput(kill_switch_active=True),
    )
    assert allowed
    assert reasons == ()
    assert status == CloakBrowserRuntimeStatus.NOT_APPLICABLE


def test_derive_policy_state_revoked():
    assert (
        derive_policy_state(
            requested=True,
            owner_admin_approved=True,
            compliance_approved=True,
            revoked_at=datetime.now(UTC),
            runtime_status=CloakBrowserRuntimeStatus.OK,
        )
        == CloakBrowserPolicyState.REVOKED
    )


def test_evaluate_runtime_policy_version_mismatch():
    assert (
        evaluate_runtime_policy(
            CloakBrowserRuntimePolicyInput(pinned_version="1.0.0", runtime_version="2.0.0")
        )
        == CloakBrowserRuntimeStatus.VERSION_MISMATCH
    )