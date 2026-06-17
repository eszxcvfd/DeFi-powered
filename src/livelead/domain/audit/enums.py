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
    WATCHLIST_UPSERTED = "watchlist.upserted"
    WATCHLIST_REMOVED = "watchlist.removed"
    WATCHLIST_DENIED = "watchlist.denied"
    EVENT_OVERRIDE_UPSERTED = "event.override.upserted"
    EVENT_OVERRIDE_CLEARED = "event.override.cleared"
    EVENT_OVERRIDE_DENIED = "event.override.denied"
    DISCOVERY_SCHEDULE_CREATED = "discovery.schedule.created"
    DISCOVERY_SCHEDULE_UPDATED = "discovery.schedule.updated"
    DISCOVERY_SCHEDULE_DISPATCHED = "discovery.schedule.dispatched"
    QUERY_EXPANSION_GENERATED = "query_expansion.generated"
    QUERY_EXPANSION_UPDATED = "query_expansion.updated"
    QUERY_EXPANSION_APPROVED = "query_expansion.approved"
    DISCOVERY_COPILOT_RESPONDED = "discovery_copilot.responded"
    DISCOVERY_COPILOT_ACCEPTED = "discovery_copilot.accepted"
    AI_FEEDBACK_RECORDED = "ai_feedback.recorded"
    SCORING_SUGGESTION_GENERATED = "scoring_suggestion.generated"
    SCORING_SUGGESTION_APPROVED = "scoring_suggestion.approved"
    SCORING_SUGGESTION_REJECTED = "scoring_suggestion.rejected"
    ENVIRONMENT_MODE_CHANGED = "environment.mode.changed"
    ENVIRONMENT_PAUSED = "environment.paused"
    ENVIRONMENT_ROLLED_BACK = "environment.rolled_back"
    ENVIRONMENT_TOGGLE_CHANGED = "environment.toggle.changed"
    BACKUP_SNAPSHOT_RECORDED = "backup.snapshot.recorded"
    BACKUP_SNAPSHOT_VERIFIED = "backup.snapshot.verified"
    BACKUP_SNAPSHOT_FAILED = "backup.snapshot.failed"
    WORKER_HEARTBEAT_RECORDED = "worker.heartbeat.recorded"
    ALERT_RULE_CREATED = "alert.rule.created"
    ALERT_RULE_UPDATED = "alert.rule.updated"
    ALERT_RULE_DELETED = "alert.rule.deleted"
    ALERT_FIRED = "alert.fired"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_AUTO_RESOLVED = "alert.auto_resolved"
    METRICS_EXPORT_POLICY_UPDATED = "metrics.export_policy.updated"
    METRICS_EXPORT_POLICY_DENIED = "metrics.export_policy.denied"
    METRICS_EXPORTED = "metrics.exported"
    METRICS_EXPORT_REJECTED = "metrics.export_rejected"
    METRICS_TEST_RUN = "metrics.test_run"
    BACKUP_RESTORE_REHEARSED = "backup.restore.rehearsed"
    BACKUP_RESTORE_SUCCEEDED = "backup.restore.succeeded"
    BACKUP_RESTORE_FAILED = "backup.restore.failed"
    BACKUP_RETENTION_PRUNED = "backup.retention.pruned"
    DATA_LEAD_DELETED = "data.lead.deleted"
    DATA_USER_DELETED = "data.user.deleted"
    DATA_OBSERVATION_DELETED = "data.observation.deleted"
    PERFORMANCE_SCENARIO_COMPLETED = "performance.scenario.completed"
    PERFORMANCE_SCENARIO_REJECTED = "performance.scenario.rejected"
    BROWSER_SESSION_BUDGET_EXCEEDED = "browser.session.budget_exceeded"
    # US-045 — event calendar export (ICS) baseline. Each
    # event type maps to a single calendar export surface
    # path. The audit entry shape is the same as the
    # existing surface; the secret-safe payload contract
    # from `US-041` is enforced before persistence.
    CALENDAR_EVENT_EXPORTED = "calendar.event.exported"
    CALENDAR_WATCHLIST_EXPORTED = "calendar.watchlist.exported"
    CALENDAR_FILTER_EXPORTED = "calendar.filter.exported"
    CALENDAR_TOKEN_MINTED = "calendar.token.minted"
    CALENDAR_TOKEN_REVOKED = "calendar.token.revoked"
    CALENDAR_TOKEN_USED = "calendar.token.used"
    # US-046 — connector health surface baseline. Each
    # event type maps to a single connector health
    # surface path. The audit entry shape reuses the
    # existing `AuditEntryRow` from `US-026`; the
    # secret-safe payload contract from `US-041` is
    # enforced before persistence.
    CONNECTOR_HEALTH_SNAPSHOT_COMPUTED = "connector.health.snapshot.computed"
    CONNECTOR_HEALTH_SUMMARY_REQUESTED = "connector.health.summary.requested"
    CONNECTOR_HEALTH_ERRORS_REQUESTED = "connector.health.errors.requested"
    CONNECTOR_HEALTH_SNAPSHOT_REJECTED = "connector.health.snapshot.rejected"
    # US-047 — internationalization and timezone baseline. Each
    # event type maps to a single i18n surface path. The
    # audit entry shape reuses the existing `AuditEntryRow`
    # from `US-026`; the secret-safe payload contract from
    # `US-041` is enforced before persistence.
    USER_LOCALE_UPDATED = "user.locale.updated"
    ORGANIZATION_LOCALE_UPDATED = "organization.locale.updated"
    LOCALE_UNSUPPORTED_REJECTED = "locale.unsupported.rejected"
    # US-048 — connector auto-disable and policy recovery
    # baseline. Each event type maps to a single
    # auto-disable surface path. The audit entry shape
    # reuses the existing `AuditEntryRow` from `US-026`;
    # the secret-safe payload contract from `US-041` is
    # enforced before persistence.
    CONNECTOR_AUTO_DISABLE_RULE_CREATED = "connector.auto_disable.rule.created"
    CONNECTOR_AUTO_DISABLE_RULE_UPDATED = "connector.auto_disable.rule.updated"
    CONNECTOR_AUTO_DISABLE_RULE_DELETED = "connector.auto_disable.rule.deleted"
    CONNECTOR_AUTO_DISABLE_TRIGGERED = "connector.auto_disable.triggered"
    CONNECTOR_AUTO_DISABLE_RECOVERED = "connector.auto_disable.recovered"
    CONNECTOR_AUTO_DISABLE_RECOVERY_RESOLVED = "connector.auto_disable.recovery.resolved"
    CONNECTOR_AUTO_DISABLE_RECOVERY_REJECTED = "connector.auto_disable.recovery.rejected"
    # US-049 — governed webhook delivery baseline. Each
    # event type maps to a single webhook surface
    # path. The audit entry shape reuses the existing
    # `AuditEntryRow` from `US-026`; the secret-safe
    # payload contract from `US-041` is enforced
    # before persistence.
    WEBHOOK_SUBSCRIPTION_CREATED = "webhook.subscription.created"
    WEBHOOK_SUBSCRIPTION_UPDATED = "webhook.subscription.updated"
    WEBHOOK_SUBSCRIPTION_DELETED = "webhook.subscription.deleted"
    WEBHOOK_SUBSCRIPTION_SECRET_ROTATED = "webhook.subscription.secret_rotated"
    WEBHOOK_SUBSCRIPTION_TEST_SENT = "webhook.subscription.test_sent"
    WEBHOOK_DELIVERY_SUCCEEDED = "webhook.delivery.succeeded"
    WEBHOOK_DELIVERY_FAILED = "webhook.delivery.failed"
    WEBHOOK_DELIVERY_DEAD_LETTER = "webhook.delivery.dead_letter"
    WEBHOOK_DELIVERY_REJECTED = "webhook.delivery.rejected"
    WEBHOOK_DELIVERY_RETRIED = "webhook.delivery.retried"
    # US-050 — lead CSV import/export baseline. Each
    # event type maps to a single lead import/export
    # surface path. The audit entry shape reuses the
    # existing `AuditEntryRow` from `US-026`; the
    # secret-safe payload contract from `US-041` is
    # enforced before persistence.
    LEAD_IMPORT_PREVIEWED = "lead.import.previewed"
    LEAD_IMPORT_APPLIED = "lead.import.applied"
    LEAD_IMPORT_DENIED = "lead.import.denied"
    LEAD_EXPORT_DOWNLOADED = "lead.export.downloaded"
    LEAD_EXPORT_DENIED = "lead.export.denied"


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
    ALERT_RULE = "alert_rule"
    ALERT_EVENT = "alert_event"
    SYSTEM = "system"
    EVENT = "event"
    WATCHLIST_ENTRY = "watchlist_entry"
    DISCOVERY_SCHEDULE = "discovery_schedule"
    QUERY_EXPANSION_SET = "query_expansion_set"
    DISCOVERY_COPILOT_RESPONSE = "discovery_copilot_response"
    AUDIENCE_HYPOTHESIS = "audience_hypothesis"
    CAMPAIGN = "campaign"
    SCORING_SUGGESTION_SET = "scoring_suggestion_set"
    ENVIRONMENT = "environment"
    LIVE_INTEGRATION_TOGGLE = "live_integration_toggle"
    BACKUP_SNAPSHOT = "backup_snapshot"
    WORKER = "worker"
    METRICS_EXPORT_POLICY = "metrics_export_policy"
    BACKUP_RESTORE_RUN = "backup_restore_run"
    RETENTION_POLICY = "retention_policy"
    PERFORMANCE_SNAPSHOT = "performance_snapshot"
    CALENDAR_EXPORT_TOKEN = "calendar_export_token"
    CALENDAR_EXPORT_AUDIT = "calendar_export_audit"
    CONNECTOR_HEALTH_SNAPSHOT = "connector_health_snapshot"
    CONNECTOR_HEALTH_ERROR = "connector_health_error"
    CONNECTOR_AUTO_DISABLE_RULE = "connector_auto_disable_rule"
    CONNECTOR_AUTO_DISABLE_EVENT = "connector_auto_disable_event"
    WEBHOOK_SUBSCRIPTION = "webhook_subscription"
    WEBHOOK_DELIVERY = "webhook_delivery"
    LEAD_IMPORT_JOB = "lead_import_job"
    LEAD_IMPORT_ROW = "lead_import_row"
