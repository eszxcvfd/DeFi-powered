"""Audit enums (US-026)."""

from __future__ import annotations

from enum import StrEnum


class AuditActorType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"
    SYSTEM = "system"


class AuditOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SYSTEM_RECORDED = "system_recorded"


class AuditAction(StrEnum):
    LOGIN_SUCCEEDED = "auth.login.succeeded"
    LOGIN_FAILED = "auth.login.failed"
    SOURCE_POLICY_DENIED = "source.policy.denied"
    SOURCE_POLICY_CHANGED = "source.policy.changed"
    CLOAKBROWSER_REQUESTED = "cloakbrowser.policy.requested"
    CLOAKBROWSER_OWNER_APPROVED = "cloakbrowser.policy.owner_approved"
    CLOAKBROWSER_COMPLIANCE_APPROVED = "cloakbrowser.policy.compliance_approved"
    CLOAKBROWSER_REVOKED = "cloakbrowser.policy.revoked"
    CLOAKBROWSER_KILL_SWITCH = "cloakbrowser.kill_switch.changed"
    CLOAKBROWSER_LAUNCH_DENIED = "cloakbrowser.launch.denied"
    CONTENT_SUBMITTED_FOR_REVIEW = "content.review.submitted"
    CONTENT_APPROVED = "content.review.approved"
    CONTENT_REJECTED = "content.review.rejected"
    BROWSER_CONFIRMATION_CONFIRMED = "browser.action.confirmation.confirmed"
    BROWSER_CONFIRMATION_CANCELLED = "browser.action.confirmation.cancelled"
    BROWSER_LAUNCH_DENIED = "browser.launch.denied"
    LEAD_STAGE_CHANGED = "lead.stage.changed"
    AUTH_LOGIN_SUCCEEDED = "auth.login.succeeded"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.session.revoked"
    AUTH_SESSION_ROTATED = "auth.session.rotated"
    AUTH_ACCESS_DENIED = "auth.access.denied"
    MEMBER_INVITED = "member.invited"
    MEMBER_INVITATION_REVOKED = "member.invitation.revoked"
    MEMBER_INVITATION_ACCEPTED = "member.invitation.accepted"
    MEMBER_ROLE_CHANGED = "member.role.changed"
    MEMBER_DISABLED = "member.disabled"
    MEMBER_ENABLED = "member.enabled"
    MEMBER_ACCESS_REVOKED = "member.access.revoked"
    MEMBER_GOVERNANCE_DENIED = "member.governance.denied"
    NOTIFICATION_PREFERENCE_CHANGED = "notification.preference_changed"
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_SUPPRESSED = "notification.suppressed"
    NOTIFICATION_DELIVERY_FAILED = "notification.delivery_failed"


class AuditTargetType(StrEnum):
    SOURCE = "source"
    CLOAKBROWSER_POLICY = "cloakbrowser_policy"
    CONTENT_DRAFT = "content_draft"
    BROWSER_SESSION = "browser_session"
    BROWSER_CONFIRMATION = "browser_confirmation"
    LEAD = "lead"
    SESSION = "session"
    USER = "user"
    MEMBERSHIP = "membership"
    INVITATION = "invitation"
    NOTIFICATION = "notification"
    NOTIFICATION_PREFERENCE = "notification_preference"
    NOTIFICATION_DELIVERY = "notification_delivery"
    WORKFLOW = "workflow"
    SYSTEM = "system"
