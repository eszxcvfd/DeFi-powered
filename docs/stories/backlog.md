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
- `US-041-operational-observability-and-alerting-baseline`: **planned** —
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
- `US-042-external-metrics-pipeline-baseline`: **planned** — first
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
