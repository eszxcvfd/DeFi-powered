# Story Backlog

This backlog will be populated after a user provides a project spec or selects a
specific initiative.

Do not create every possible story packet up front. Create story packets when
the work is selected or when a product decision needs a durable place to land.
## Candidate Epics

| Epic | Description | Status |
| --- | --- | --- |
| E00 Foundation | Repository scaffold, selected stack, local dev services, auth/RBAC boundary, tenant model, audit foundation, and validation commands. | active |
| E01 Discovery MVP | Campaign/ICP, source registry and policy, API/RSS connector, browser adapter contract, discovery job progress, event normalization, deduplication, event list/detail. | active |
| E02 Intelligence | Event scoring, audience hypothesis, evidence linking, AI provider abstraction, engagement plan, generated content, review workflow, anti-spam guardrails. | active |
| E03 Lead And Reporting | Lead pipeline, duplicate detection, activities, follow-up reminders, dashboard, funnel, source performance, export. | active |
| E04 Browser-Assisted Operations | Supporting browser session governance, confirmation workflow, screenshots/traces, profile lifecycle, and optional CloakBrowser adapter review for permitted-source access. | active |
| E05 Hardening | Performance, security, observability, backup/restore, UAT, and production readiness. | active |
| E06 Calendar Export | Calendar export (ICS) for events, watchlists, and event filter sets, with tokenized feed, audit entry shape, and follow-on calendar auth and shared-watchlist seam. | active |

## First Story Candidates

- `US-001-foundation-baseline`: create the first implementation scaffold and
  proof ladder for the selected stack.
- `US-002-campaign-icp-contract`: define campaign and ICP commands, queries,
  validation, and minimal UI/API behavior.
- `US-003-source-policy-registry`: create source registry and policy enforcement
  before any connector work.
- `US-004-discovery-job-lifecycle`: run a manual discovery job with deterministic
  mock connector proof before live external sources.
- `US-005-event-results-baseline`: normalize discovery output into canonical
  events with provenance-aware deduplication and a minimal review surface.
- `US-006-event-scoring-baseline`: calculate campaign-aware event scores with
  explainable priority breakdown and explicit re-score behavior.
- `US-007-audience-hypothesis-baseline`: generate explainable audience
  hypotheses with evidence links and sensitive-inference guardrails.
- `US-008-engagement-plan-baseline`: create phase-based engagement plans and
  task tracking before content generation or approval workflow.
- `US-009-content-generation-baseline`: generate editable draft variants with
  safety flags before approval workflow or export behavior.
- `US-010-content-approval-baseline`: add reviewer approval and rejection
  workflow before export, used-lifecycle, or sending behavior.
- `US-011-content-handoff-baseline`: allow approved-only copy/export and
  used-state handoff before browser-send or archive workflow.
- `US-012-lead-pipeline-baseline`: create the first lead pipeline slice with
  event or manual lead creation, default stages, duplicate guardrails, and
  baseline activity history before reminders or reporting.
- `US-013-follow-up-reminders-baseline`: turn lead follow-up dates into due or
  overdue reminder work, in-app reminder visibility, and complete or reschedule
  actions before dashboard or email-notification stories.
- `US-014-dashboard-overview-baseline`: add the first date-range dashboard
  overview with trustworthy summary cards, freshness metadata, and explicit
  empty or unavailable states before funnel, source-performance, or export
  reporting.
- `US-015-lead-outcomes-baseline`: add the first manual outcome-tracking slice
  for contact, response, meeting, and opportunity milestones before funnel,
  content-effectiveness, or CRM-sync stories.
- `US-016-funnel-baseline`: add the first conversion funnel report from event to
  lead to contact/response/meeting/opportunity with explicit cohort rules before
  source-performance, content-effectiveness, or export stories.
- `US-017-source-performance-baseline`: add the first grouped source-performance
  report by platform, connector, campaign, and industry before
  content-effectiveness or export stories.
- `US-018-content-effectiveness-baseline`: add the first grouped
  content-effectiveness report by content type, tone, and template metadata
  before export stories.
- `US-019-report-export-baseline`: add the first report-export slice for
  dashboard, funnel, source-performance, and content-effectiveness views with
  CSV and printable output before scheduled delivery or external report-sync
  stories.
- `US-020-browser-session-baseline`: add the first supervised browser-session
  slice with session launch, isolation, live status, and safe stop before
  allowlisted actions, confirmation flows, profile lifecycle, or debug-artifact
  stories.
- `US-021-read-only-browser-actions-baseline`: add the first allowlisted
  read-only browser-action slice with selector guardrails and timeout budgets
  before destructive confirmation, screenshot/trace, or profile-management
  stories.
- `US-022-confirmation-gated-browser-actions-baseline`: add the first preview,
  dry-run, and explicit confirmation slice for destructive or external-side-
  effect browser actions before screenshot/trace, profile-management, or
  CloakBrowser policy stories.
- `US-023-browser-debug-artifacts-baseline`: add the first governed debug-
  artifact slice for supervised browser sessions with manual screenshot,
  console-log/trace capture, and retention/access guardrails before profile-
  management or CloakBrowser policy stories.
- `US-024-browser-profile-lifecycle-baseline`: add the first governed browser-
  profile lifecycle slice with consented storage-state handling, lock/expire/
  delete controls, and blocked-session reuse rules before CloakBrowser policy
  stories.
- `US-025-cloakbrowser-policy-baseline`: add the first CloakBrowser governance
  slice with source-scoped approval gates, runtime provenance checks, and kill-
  switch controls while keeping the optional engine disabled by default.
- `US-026-audit-log-baseline`: add the first admin audit-log slice with
  tenant-scoped, append-only, secret-safe action history and governed filters
  before retention-policy, data-deletion, or connector-health stories.
- `US-027-identity-access-baseline`: replace header-based dev auth with the
  first authenticated session, tenant membership, backend RBAC, generic login-
  failure handling, and audit-safe denial flow before member management, email
  notifications, or SSO federation stories.
- `US-028-member-management-baseline`: add the first member-governance slice
  with invitations, invite acceptance, role change, disable/re-enable, revoke
  access, and last-owner guardrails before email delivery, SCIM, or enterprise
  SSO administration stories.
- `US-029-notification-delivery-baseline`: add the first governed notification
  slice with in-app alerts, email delivery for selected reminder/job/event
  cases, and per-user notification preferences before watchlist automation,
  digest scheduling, or external channel integrations.
- `US-030-event-watchlist-baseline`: add the first user-scoped event watchlist
  slice with reminder scheduling, watched-state filters, and saved-event revisit
  flows before calendar export, bulk watchlist actions, or shared-team
  watchlists.
- `US-031-event-manual-overrides-baseline`: add the first governed canonical
  event-edit slice with override protection, clear-override behavior, and
  change history before bulk edit, calendar export, or advanced event-sync
  stories.
- `US-032-live-feed-api-discovery-baseline`: add the first real external
  discovery slice with governed `API`/`RSS`/`ICS` connectors, policy-aware job
  execution, and canonical-event ingestion before Playwright, Selenium, or
  scheduled sync stories.
- `US-033-public-website-playwright-discovery-baseline`: add the first public
  website discovery slice with governed `Playwright` recipes, policy-aware
  browser extraction, and canonical-event ingestion before Selenium, login-
  required browsing, or broader browser-console stories.
- `US-034-selenium-adapter-discovery-baseline`: implemented — governed
  `Selenium`/alternate-adapter discovery with source-scoped engine selection,
  policy-aware extraction, and canonical-event ingestion.
- `US-035-scheduled-discovery-baseline`: add the first bounded recurring
  discovery slice with daily/weekly/restricted-cron schedules, scheduler
  dispatch, overlap protection, and standard discovery-job visibility before
  query expansion or discovery-copilot stories.
- `US-036-query-expansion-baseline`: **implemented** — governed query expansion,
  grouped variants, approval-required AI suggestions, immutable job/schedule
  snapshots; `./scripts/verify-us-036.sh`.
- `US-037-discovery-copilot-baseline`: **implemented** — structured copilot
  responses (Gemini or deterministic), accept → query expansion; Google AI Studio
  via `LIVELEAD_GOOGLE_AI_STUDIO_API_KEY`; `./scripts/verify-us-037.sh`;
  see `docs/RUNTIME_CONFIGURATION.md`.
- `US-038-ai-feedback-signals-baseline`: **implemented** — governed AI feedback
  for copilot and audience targets; `./scripts/verify-us-038.sh`;
  `docs/product/ai-feedback-and-learning-signals.md`.
- `US-039-feedback-learning-scoring-suggestions`: **implemented** — reviewable
  scoring-weight suggestions from campaign feedback, approval-gated snapshots;
  `./scripts/verify-us-039.sh`; `docs/decisions/0017-scoring-suggestion-feedback-learning-baseline.md`.
- `US-040-real-environment-pilot-cutover`: **implemented** — pilot-live
  cutover slice with launch gate, live toggles, backup metadata, and
  guarded rollback; `./scripts/verify-us-040.sh`;
  `docs/decisions/0018-pilot-live-cutover-baseline.md`;
  `docs/ops/pilot-live-cutover-runbook.md`;
  `docs/ops/pilot-live-pause-runbook.md`;
  `docs/ops/pilot-live-rollback-runbook.md`.
- `US-041-operational-observability-and-alerting-baseline`: **implemented** —
  first bounded observability and alerting slice that consumes the
  `US-040` runtime readiness contract and the `US-026` audit log; durable
  `AlertRule` and `AlertEvent` tables, secret-safe payload helper, evaluator
  with cooldown, in-app inbox and email delivery reused from `US-029`,
  `GET /admin/observability/summary`, and seed rules for stale backup,
  missing worker heartbeat, connector failure spike, discovery
  `NEEDS_USER_ACTION` storm, browser crash loop, and audit retention
  breach risk; `docs/stories/epics/E05-hardening/US-041-operational-observability-and-alerting-baseline/`;
  `docs/product/observability-and-alerting.md`;
  `docs/decisions/0019-observability-and-alerting-baseline.md`.
- `US-042-external-metrics-pipeline-baseline`: **implemented** — first
  external metrics pipeline slice that closes the deferred follow-up
  in `0019` and ships a vendor-agnostic, local-first export side for
  the `US-041` observability contract; durable `MetricsExportPolicy`
  table, closed `MetricRegistry` mirroring the `SignalProvider` enum,
  pluggable `ExportTransport` Protocol with three concrete transports
  (`PrometheusExposition`, `OtelCollector`, `SentryIngest`), secret-safe
  payload reuse from `US-041`, owner/admin REST surface for policy
  management and `Test export`, `GET /metrics` endpoint gated by a
  per-workspace scrape token and an allowlist of source CIDRs,
  OpenTelemetry tracer integration, Sentry error reporter integration,
  operator panel widget, and `docs/ops/metrics-export-runbook.md`;
  `docs/stories/epics/E05-hardening/US-042-external-metrics-pipeline-baseline/`;
  `docs/product/external-metrics-and-tracing.md`;
  `docs/decisions/0020-external-metrics-pipeline-baseline.md`.
- `US-043-backup-and-restore-operations-baseline`: **implemented** —
  first bounded backup and restore operations slice that closes the
  gap left by `US-040` (the `BackupSnapshot` table exists but no
  restore workflow) and the deferred restore rehearsal commitment
  referenced by `US-041` and `US-042`; durable `BackupRestoreRun` and
  `RetentionPolicy` tables, bounded `BackupRestoreService` with
  `dry_run_restore`, `schedule_rehearsal`, `restore_backup`, and
  `prune_expired_backups`, governed `DataDeletionService` for lead,
  user, and source observation deletion, secret-safe payload reuse
  from `US-041`, owner/admin REST surface for restore, retention,
  and data-deletion, restore rehearsal actor, retention prune actor,
  operator panel widget, and `docs/ops/backup-restore-runbook.md`;
  addresses `NFR-REL-005` (RPO 24h, RTO 8h), `FR-ADM-004`, and
  `FR-ADM-005`; `docs/stories/epics/E05-hardening/US-043-backup-and-restore-operations-baseline/`;
  `docs/product/backup-and-restore-operations.md`;
  `docs/decisions/0021-backup-and-restore-operations-baseline.md`.
- `US-046-connector-health-surface-baseline`: **planned** — first
  bounded connector health surface slice that closes `FR-ADM-002`
  and the explicit follow-up committed in `0019`; durable
  `connector_health_snapshots` and `connector_health_errors` tables,
  closed `ConnectorHealthStatus` enum (`healthy`, `degraded`,
  `unhealthy`, `unknown`), bounded `ConnectorHealthService` with
  `compute_snapshot`, `list_snapshots`, `build_summary`, and
  `list_recent_errors`, `ConnectorHealthComputer` that derives the
  bounded metrics from `discovery_jobs` and `audit_entries`, bounded
  window by the `EnvironmentMode` from `US-040` (max 24 hours in
  `pilot_live`, max 1 hour in `test_like`), secret-safe payload
  reuse from `US-041`, owner/admin-only REST surface
  (`GET /admin/connectors/health/summary`,
  `GET /admin/connectors/health/snapshots`,
  `POST /admin/connectors/health/snapshots:compute`,
  `GET /admin/connectors/{source_id}/health/errors`),
  `MetricRegistry` extension from `US-042`, `AlertMetric` enum
  extension from `US-041`, operator panel widget, in-app inbox
  entries from `US-029`, and `docs/ops/connector-health-runbook.md`;
  `docs/stories/epics/E05-hardening/US-046-connector-health-surface-baseline/`;
  `docs/product/connector-health-surface.md`;
  `docs/decisions/0024-connector-health-surface-baseline.md`.
- `US-045-event-calendar-export-ics-baseline`: **implemented** — first
  bounded calendar export (ICS) slice that turns `FR-EVT-005` and the
  explicit gap from `US-030` design into a documented contract,
  a per-user ICS export endpoint, a tokenized calendar feed, and
  a reusable export-token surface; durable `CalendarExportToken`
  and `CalendarExportAudit` tables, closed `CalendarScope` enum
  (`event`, `watchlist`, `event_filter`), bounded
  `CalendarExportService` with `build_event_ics`,
  `build_watchlist_ics`, `build_filter_ics`, `mint_token`,
  `revoke_token`, and `resolve_token`, calendar `STATUS` mapping
  (`UPCOMING` → `TENTATIVE`, `LIVE` → `CONFIRMED`, `ENDED` →
  `CANCELLED`), token TTL bound by the `EnvironmentMode` from
  `US-040` (max 90 days in `pilot_live`, max 30 days in
  `test_like`), secret-safe payload reuse from `US-041`, current-
  user REST surface (`GET /events/{id}.ics`,
  `GET /watchlist/events.ics`, `GET /events.ics`,
  `POST /calendar-export-tokens`,
  `GET /calendar-export-tokens`,
  `DELETE /calendar-export-tokens/{id}`) and tokenized REST
  surface (`GET /calendar-export/{token}.ics`), calendar export
  modal, calendar exports panel, in-app inbox entries from
  `US-029`, and `docs/ops/calendar-export-runbook.md`;
  `docs/stories/epics/E01-discovery-mvp/US-045-event-calendar-export-ics-baseline/`;
  `docs/product/event-calendar-export.md`;
  `docs/decisions/0023-event-calendar-export-ics-baseline.md`.
- `US-044-performance-baseline-and-slo-guardrails`: **implemented** —
  first bounded performance baseline and SLO guardrails slice
  that addresses `NFR-PERF-001..005` (API read latency, event
  list pagination, discovery job first progress, concurrency
  cap, browser session budget); durable `PerformanceSnapshot`
  table, closed `PerformanceMetric` enum extending the `US-041`
  `AlertMetric` enum and the `US-042` `MetricRegistry`, seed
  SLO alert rule set in the `US-041` migration, bounded
  `PerformanceBaselineService` with `run_scenario`,
  `list_snapshots`, and `build_summary`,
  `BrowserSessionBudgetEnforcer` extending the `US-020`
  browser session worker, secret-safe payload reuse from
  `US-041`, owner/admin REST surface for the SLO summary,
  snapshots, and scenario runner, in-process bounded
  load-test harness in `scripts/verify-us-044.sh`, operator
  panel widget, and `docs/ops/performance-baseline-runbook.md`;
  `docs/stories/epics/E05-hardening/US-044-performance-baseline-and-slo-guardrails/`;
  `docs/product/performance-baseline-and-slo-guardrails.md`;
  `docs/decisions/0022-performance-baseline-and-slo-guardrails.md`.
- `US-047-internationalization-and-timezone-baseline`:
  **implemented** — first bounded internationalization
  and timezone baseline slice that closes
  `NFR-I18N-001` (separate strings from code,
  `vi-VN`/`en-US`), `NFR-I18N-002` (UTC storage +
  user timezone display), and `NFR-I18N-003`
  (Unicode, diacritics, normalization) and the
  explicit follow-up committed in the production
  readiness review from `SPEC.md` section 17;
  durable `users.locale`, `users.timezone`,
  `organizations.default_locale`, and
  `organizations.default_timezone` columns, closed
  `Locale` enum (`vi-VN`, `en-US`), bounded
  `Timezone` IANA validation,
  `I18nService` with `resolve_locale`,
  `resolve_timezone`, `format_datetime`,
  `format_date`, `format_time`,
  `parse_user_locale`, and
  `parse_user_timezone`, current-user REST
  surface (`GET /me/locale`,
  `PATCH /me/locale`) and owner/admin REST
  surface
  (`GET /admin/organizations/{id}/locale`,
  `PATCH /admin/organizations/{id}/locale`),
  audit entries for `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected` reusing the
  secret-safe payload contract from `US-026`
  and `US-041`, Unicode normalization (NFC) for
  `vi-VN` search queries, locale switcher on
  the user menu, admin surface on the
  organization settings page, reusable
  `useLocale()` hook, reusable
  `<LocalizedDatetime>`, `<LocalizedDate>`,
  and `<LocalizedTime>` components,
  minimum-viable `text_catalog` JSON dictionary
  under `frontend/src/locales/{locale}.json`,
  migration forward-safety and rollback,
  and `scripts/verify-us-047.sh`;
  `docs/stories/epics/E05-hardening/US-047-internationalization-and-timezone-baseline/`;
  `docs/product/internationalization-and-timezone.md`;
  `docs/decisions/0025-internationalization-and-timezone-baseline.md`.
- `US-048-connector-auto-disable-and-policy-recovery-baseline`:
  **planned** — first bounded connector
  auto-disable and policy recovery slice that
  closes the implicit `FR-SRC-004` + `SPEC.md`
  11.1 kill-switch requirements; durable
  `connector_auto_disable_rules` and
  `connector_auto_disable_events` tables,
  closed `AutoDisableTrigger` and
  `AutoDisableEventStatus` enums, bounded
  `AutoDisableService` and
  `AutoDisableEvaluator`, human-confirmed
  recovery flow, source-side helper
  `evaluate_source_for_discovery` that
  refuses to dispatch a discovery job
  against an `auto_disabled` source, owner
  /admin-only REST surface, bounded window
  bound by the `EnvironmentMode` from
  `US-040`, secret-safe payload reuse from
  `US-041`, audit entries from `US-026`,
  closed connector health status reuse
  from `US-046`, RBAC contract from
  `US-027`, source registry extension of
  `US-003`, runbook
  `docs/ops/connector-auto-disable-runbook.md`,
  decision
  `docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`,
  and `scripts/verify-us-048.sh`;
  `docs/stories/epics/E05-hardening/US-048-connector-auto-disable-and-policy-recovery-baseline/`;
  `docs/product/connector-auto-disable-and-recovery.md`.
- `US-049-governed-webhook-delivery-baseline`:
  **planned** — first bounded governed
  webhook delivery slice that closes
  `SPEC.md` §7.4 (Webhook with HMAC
  signing, timestamp anti-replay, and
  retry policy); durable
  `webhook_subscriptions` and
  `webhook_deliveries` tables, closed
  `WebhookEventType` and
  `WebhookDeliveryStatus` enums, bounded
  `WebhookDeliveryService` with
  `WebhookSigner` HMAC-SHA256 helper and
  `WebhookRetryPolicy` (exponential
  backoff + bounded jitter), bounded
  `WebhookDispatcher` actor, bounded
  secret rotation helper that reuses the
  `US-003` secret manager, bounded target
  URL allowlist that refuses private IP
  addresses, bounded window bound by the
  `EnvironmentMode` from `US-040`,
  secret-safe payload reuse from
  `US-041`, audit entries from `US-026`,
  RBAC contract from `US-027`, runbook
  `docs/ops/webhook-delivery-runbook.md`,
  decision
  `docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`,
  and `scripts/verify-us-049.sh`;
  `docs/stories/epics/E05-hardening/US-049-governed-webhook-delivery-baseline/`;
  `docs/product/webhook-delivery-and-event-fanout.md`.
