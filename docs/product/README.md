# LiveLead Product Docs

Source of truth hierarchy:

1. `SPEC.md`
2. accepted decisions in `docs/decisions/`
3. product-domain files in this directory

This directory now contains the living product contract for LiveLead, broken
into smaller domain files so future stories can update only the surfaces they
actually change.

## Core Docs

- `overview.md`: product summary, principles, roles, and non-goals.
- `mvp-scope-and-priorities.md`: seven core jobs, guardrails, and priority
  rules.
- `identity-and-access.md`: login, session, RBAC, and tenant-isolation
  contract.
- `member-management-and-access-governance.md`: invitations, role changes,
  disable/revoke rules, and admin membership governance.
- `notification-delivery-and-preferences.md`: in-app alerts, email delivery,
  and per-user notification controls.
- `campaign-and-icp.md`: campaign input, natural-language brief parsing, ICP,
  target-market mix.
- `source-registry-and-policy.md`: governed source catalog and channel policy.
- `discovery-job-lifecycle.md`: discovery launch, progress, state model, and
  structured criteria snapshots.
- `scheduled-discovery-and-sync.md`: first bounded recurring discovery contract
  with scheduler dispatch and overlap guardrails.
- `query-expansion-and-review.md`: first governed discovery-query expansion
  contract with grouped variants and approval-required AI suggestions.
- `discovery-copilot-and-structured-briefing.md`: first governed natural-
  language discovery-copilot contract with structured grounded responses.
- `ai-feedback-and-learning-signals.md`: first governed AI-feedback contract for
  discovery-copilot and audience-analysis outputs without auto-learning.
- `feedback-learning-and-scoring-suggestions.md`: first governed scoring-weight
  suggestion contract derived from feedback signals with explicit approval.
- `real-environment-cutover-and-live-operations.md`: first governed pilot-live
  cutover contract for running the system in a real environment beyond test-only
  proof.
- `observability-and-alerting.md`: first operational observability and
  alerting contract that turns durable runtime signals into secret-safe
  alerts and a single operator view.
- `external-metrics-and-tracing.md`: first external metrics pipeline
  contract that exports the `observability-and-alerting` signals to a
  Prometheus scrape target, an OpenTelemetry collector, and a Sentry
  project behind the `SanitizeAlertPayload` helper and the closed
  `MetricRegistry`.
- `backup-and-restore-operations.md`: first bounded backup and
  restore operations contract that turns the `BackupSnapshot` metadata
  from `real-environment-cutover-and-live-operations` into a usable
  contract — restore rehearsal, retention enforcement, and governed
  data deletion behind owner/admin role gates.
- `performance-baseline-and-slo-guardrails.md`: first bounded
  performance baseline contract that turns `NFR-PERF-001..005` into a
  documented baseline, a set of SLO alert rules, a browser session
  budget enforcement path, and a bounded load-test harness behind
  the `US-041` alert evaluator and the `US-042` metric registry.
- `live-feed-and-api-discovery.md`: first real external `API`/`RSS`/`ICS`
  discovery contract and safe canonical-event ingestion.
- `public-website-playwright-discovery.md`: first governed `Playwright`
  website-discovery contract and browser-recipe extraction baseline.
- `selenium-and-alternate-adapter-discovery.md`: first governed `Selenium` or
  alternate-adapter discovery contract and engine-selection baseline.
- `event-manual-overrides-and-history.md`: authorized canonical-event edits,
  overwrite protection, and event change history.
- `event-watchlist-and-reminders.md`: user-scoped watched events, reminder
  scheduling, and saved-event revisit workflow.
- `event-calendar-export.md`: first bounded calendar export (ICS) contract
  for single events, current-user watchlists, and current event filter
  sets with a tokenized feed surface, audit entry shape, and
  calendar `STATUS` mapping.
- `connector-health-surface.md`: first bounded connector health surface
  contract that turns `FR-ADM-002` into a documented per-connector health
  snapshot, recent-errors rollup, and closed `ConnectorHealthStatus`
  enum with sanitized payload reuse from `US-041`.
- `connector-auto-disable-and-recovery.md`: first bounded connector
  auto-disable and policy recovery contract that turns the implicit
  `FR-SRC-004` + `SPEC.md` 11.1 kill-switch requirements into a
  documented per-source auto-disable rule, per-event auto-disable
  history, closed `AutoDisableTrigger` and `AutoDisableEventStatus`
  enums, a bounded `AutoDisableService` and `AutoDisableEvaluator`,
  a human-confirmed recovery flow, and a source-side helper that
  refuses to dispatch a discovery job against an `auto_disabled`
  source. Reuses `US-046` health surface, `US-041` alerting, `US-040`
  `EnvironmentMode`, `US-026` audit, `US-003` source registry, and
  `US-027` RBAC without redefining any of them.
- `webhook-delivery-and-event-fanout.md`: first bounded governed
  webhook delivery contract that turns `SPEC.md` §7.4 (Webhook
  with HMAC signing, timestamp anti-replay, and retry policy) into
  a documented per-workspace `WebhookSubscription`, per-delivery
  `WebhookDelivery` history, closed `WebhookEventType` and
  `WebhookDeliveryStatus` enums, a bounded `WebhookDeliveryService`
  with `WebhookSigner` HMAC-SHA256 helper, a bounded
  `WebhookRetryPolicy` with exponential backoff and bounded
  jitter, a bounded `WebhookDispatcher` actor, a bounded secret
  rotation helper that reuses the `US-003` secret manager, a
  bounded target URL allowlist that refuses private IP addresses,
  and a bounded window bound by the `EnvironmentMode` from
  `US-040`. Reuses `US-003` secret manager, `US-026` audit,
  `US-029` notifications, `US-040` `EnvironmentMode`, `US-041`
  alerting, `US-048` auto-disable, and `US-027` RBAC without
  redefining any of them.
- `internationalization-and-timezone.md`: first bounded internationalization
  and timezone contract that turns `NFR-I18N-001` (`vi-VN`/`en-US`,
  separate strings from code), `NFR-I18N-002` (UTC storage + user
  timezone display), and `NFR-I18N-003` (Unicode, diacritics,
  normalization) into a closed `Locale` enum, a bounded `Timezone`
  IANA validation, an `I18nService` seam, and a per-user and
  per-organization locale/timezone surface with audit entries.
- `lead-import-export.md`: first bounded CSV import/export contract for leads
  with mapping preview, duplicate classification, create-only apply semantics,
  and audit-safe portability.
- `engagement-plans-and-tasks.md`: event-state-aware playbooks and task
  contracts.
- `generated-content-and-safety.md`: reviewable AI drafts and safety rules.
- `platform-and-automation-policy.md`: runtime and automation guardrails.
- `audit-log-and-governance.md`: admin audit history, redaction, and governance
  query surface.

## Runtime and operators

- Environment template: repo-root `.env.example` (full `LIVELEAD_*` list).
- Copilot (Gemini), query expansion, and verify commands:
  `docs/RUNTIME_CONFIGURATION.md`.
- Local processes and browser/discovery flags: `docs/FOUNDATION_RUNTIME.md`.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
