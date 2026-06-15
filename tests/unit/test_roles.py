"""Identity and access domain helpers (US-027)."""

from __future__ import annotations

import pytest

from livelead.domain.identity import (
    Role,
    can_access_admin_connector,
    can_access_audit_log,
    can_access_browser_profile,
    can_edit_campaign,
    can_edit_lead_pipeline,
    can_review_content,
    is_admin,
    is_authenticated,
    is_governance,
    is_known_role,
    is_reviewer,
    parse_role,
)


def test_role_enum_values():
    assert Role.OWNER.value == "owner"
    assert Role.ADMIN.value == "admin"
    assert Role.COMPLIANCE.value == "compliance"
    assert Role.ANALYST.value == "analyst"
    assert Role.SALES_BD.value == "sales_bd"
    assert Role.REVIEWER.value == "reviewer"
    assert Role.VIEWER.value == "viewer"


def test_is_known_role_recognises_known_values():
    assert is_known_role("admin") is True
    assert is_known_role(Role.OWNER) is True
    assert is_known_role("unknown") is False


def test_parse_role_normalises_value():
    assert parse_role("Owner") == Role.OWNER
    assert parse_role("ANALYST") == Role.ANALYST
    assert parse_role("  reviewer  ") == Role.REVIEWER
    assert parse_role("not-a-role") is None
    assert parse_role(None) is None


def test_is_admin_only_owner_and_admin():
    assert is_admin(Role.OWNER) is True
    assert is_admin(Role.ADMIN) is True
    assert is_admin(Role.COMPLIANCE) is False
    assert is_admin(Role.ANALYST) is False
    assert is_admin(None) is False


def test_is_governance_includes_compliance():
    assert is_governance(Role.OWNER) is True
    assert is_governance(Role.ADMIN) is True
    assert is_governance(Role.COMPLIANCE) is True
    assert is_governance(Role.ANALYST) is False
    assert is_governance(None) is False


def test_is_reviewer_includes_admin_and_owner():
    assert is_reviewer(Role.OWNER) is True
    assert is_reviewer(Role.ADMIN) is True
    assert is_reviewer(Role.REVIEWER) is True
    assert is_reviewer(Role.ANALYST) is False


def test_is_authenticated_includes_every_role():
    for role in Role:
        assert is_authenticated(role) is True
    assert is_authenticated(None) is False


def test_can_access_admin_connector_owner_or_admin_only():
    assert can_access_admin_connector(Role.OWNER) is True
    assert can_access_admin_connector(Role.ADMIN) is True
    assert can_access_admin_connector(Role.ANALYST) is False
    assert can_access_admin_connector(Role.REVIEWER) is False
    assert can_access_admin_connector(None) is False


def test_can_access_audit_log_governance_or_admin():
    assert can_access_audit_log(Role.OWNER) is True
    assert can_access_audit_log(Role.ADMIN) is True
    assert can_access_audit_log(Role.COMPLIANCE) is True
    assert can_access_audit_log(Role.ANALYST) is False
    assert can_access_audit_log(Role.REVIEWER) is False
    assert can_access_audit_log(None) is False


def test_can_access_browser_profile_is_authenticated():
    for role in Role:
        assert can_access_browser_profile(role) is True
    assert can_access_browser_profile(None) is False


def test_can_review_content_owner_admin_reviewer():
    assert can_review_content(Role.OWNER) is True
    assert can_review_content(Role.ADMIN) is True
    assert can_review_content(Role.REVIEWER) is True
    assert can_review_content(Role.ANALYST) is False
    assert can_review_content(Role.SALES_BD) is False


def test_can_edit_campaign_disallows_reviewer_and_viewer():
    assert can_edit_campaign(Role.OWNER) is True
    assert can_edit_campaign(Role.ADMIN) is True
    assert can_edit_campaign(Role.ANALYST) is True
    assert can_edit_campaign(Role.SALES_BD) is True
    assert can_edit_campaign(Role.REVIEWER) is False
    assert can_edit_campaign(Role.VIEWER) is False


def test_can_edit_lead_pipeline_disallows_analyst():
    assert can_edit_lead_pipeline(Role.OWNER) is True
    assert can_edit_lead_pipeline(Role.ADMIN) is True
    assert can_edit_lead_pipeline(Role.SALES_BD) is True
    assert can_edit_lead_pipeline(Role.ANALYST) is False
    assert can_edit_lead_pipeline(Role.REVIEWER) is False
    assert can_edit_lead_pipeline(Role.VIEWER) is False
