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
| E04 Browser-Assisted Operations | Headed browser session console, profile lifecycle, confirmation workflow, screenshots/traces, optional CloakBrowser adapter review. | active |
| E05 Hardening | Performance, security, observability, backup/restore, UAT, and production readiness. | unsliced |

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
