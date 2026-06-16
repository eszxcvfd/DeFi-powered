# Test Matrix

This file maps product behavior to proof.

No product behavior has been defined or implemented yet. Do not mark a row
implemented until tests or validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Foundation runtime boots (API, SQLite path, worker wiring, frontend shell) | yes | yes | yes | yes | implemented | `./scripts/verify-foundation.sh` |
| US-002 | Campaign + ICP API/UI contract, org scope, scoring weights persist | yes | yes | yes | yes | implemented | `./scripts/verify-us-002.sh` |
| US-003 | Source registry, policy deny/runnable, admin UI, encrypted secrets | yes | yes | yes | yes | implemented | `./scripts/verify-us-003.sh` |
| US-004 | Manual discovery jobs, mock connectors, progress, cancel, SSE | yes | yes | yes | yes | implemented | `./scripts/verify-us-004.sh` |
| US-005 | Canonical event review list/detail, provenance, confidence, deduplication | yes | yes | yes | yes | implemented | `./scripts/verify-us-005.sh` |
| US-006 | Campaign-aware event scoring, priority breakdown, explicit re-score | yes | yes | yes | yes | implemented | `./scripts/verify-us-006.sh` |
| US-007 | Audience hypotheses, evidence links, confidence, sensitive-inference guardrails | yes | yes | yes | yes | implemented | `./scripts/verify-us-007.sh` |
| US-008 | Engagement plans, phased tasks, task-state updates, anti-spam planning guardrails | yes | yes | yes | yes | implemented | `./scripts/verify-us-008.sh`; engagement API + `frontend/e2e/engagement-plan.spec.ts` |
| US-009 | Generated drafts, provider metadata, inline editing, and safety flags | yes | yes | yes | yes | implemented | `./scripts/verify-us-009.sh`; `POST /content/generate` + `frontend/e2e/content-generation.spec.ts` |
| US-010 | Content approval states, reviewer decisions, and review history | yes | yes | yes | yes | implemented | `./scripts/verify-us-010.sh`; approve/reject API + `frontend/e2e/content-approval.spec.ts` |
| US-011 | Approved-content copy/export, used-state updates, and handoff audit trail | yes | yes | yes | yes | implemented | `./scripts/verify-us-011.sh`; handoff API + `frontend/e2e/content-handoff.spec.ts` |
| US-012 | Lead creation, default pipeline states, duplicate guardrails, and baseline activity history | yes | yes | yes | yes | implemented | `./scripts/verify-us-012.sh`; lead API + `frontend/e2e/lead-pipeline.spec.ts` |
| US-013 | Lead-linked follow-up reminders, due/overdue queue, and baseline in-app reminder visibility | yes | yes | yes | yes | implemented | `./scripts/verify-us-013.sh`; reminders API + `frontend/e2e/follow-up-reminders.spec.ts` |
| US-014 | Dashboard overview cards, widget freshness, and explicit empty or unavailable metric states | yes | yes | yes | yes | implemented | verify-us-014.sh; /reporting/dashboard-overview + dashboard-overview.spec.ts |
| US-015 | Manual lead outcomes, timeline outcome history, and baseline content-linked conversion tracking | yes | yes | yes | yes | implemented | verify-us-015.sh; POST /leads/{id}/outcomes + lead-outcomes.spec.ts |
| US-016 | Funnel reporting from event to lead to contact/response/meeting/opportunity with explicit cohort handling | yes | yes | yes | yes | implemented | verify-us-016.sh; GET /reports/funnel + funnel-report.spec.ts |
| US-017 | Source-performance reporting by platform, connector, campaign, and industry with attributable grouped metrics | yes | yes | yes | yes | implemented | verify-us-017.sh; GET /reports/source-performance + source-performance.spec.ts |
| US-018 | Content-effectiveness reporting by content type, tone, and template metadata with linked outcome attribution | yes | yes | yes | yes | implemented | verify-us-018.sh; GET /reports/content-effectiveness + content-effectiveness.spec.ts |
| US-019 | Report export for dashboard and grouped reporting with CSV plus printable output and preserved filter context | yes | yes | yes | yes | implemented | verify-us-019.sh; GET /reports/export + report-export.spec.ts |
| US-020 | Supervised browser session launch, isolated session status, and safe stop control from UI entrypoints | yes | yes | yes | yes | implemented | verify-us-020.sh; POST/GET /browser-sessions + browser-session.spec.ts |
| US-021 | Allowlisted read-only browser actions with selector guardrails, status events, and timeout or budget enforcement | yes | yes | yes | yes | implemented | `./scripts/verify-us-021.sh` |
| US-022 | Confirmation-gated side-effect browser actions with preview or dry-run, explicit confirm/cancel, and audit context | yes | yes | yes | yes | implemented | `./scripts/verify-us-022.sh` |
| US-023 | Debug artifacts, screenshot capture, and retention guardrails for supervised browser sessions | yes | yes | yes | yes | implemented | `./scripts/verify-us-023.sh` |
| US-024 | Governed browser profile lifecycle, consented storage state, and expiry controls | yes | yes | yes | yes | implemented | `./scripts/verify-us-024.sh`; `frontend/e2e/browser-profile-lifecycle.spec.ts` |
| US-025 | CloakBrowser approval gates, source-scoped enablement, and kill-switch controls | yes | yes | yes | yes | implemented | `./scripts/verify-us-025.sh`; `frontend/e2e/cloakbrowser-policy.spec.ts` |
| US-026 | Admin audit log baseline, tenant-scoped event history, and secret-safe governance filters | yes | yes | yes | yes | implemented | `./scripts/verify-us-026.sh`; `frontend/e2e/audit-log.spec.ts` |
| US-027 | Identity access baseline with real auth, RBAC, and tenant isolation | yes | yes | yes | yes | implemented | `./scripts/verify-us-027.sh`; `frontend/e2e/identity-access.spec.ts` |
| US-028 | Member management baseline with invitations and governed access changes | yes | yes | yes | yes | implemented | `./scripts/verify-us-028.sh`; `frontend/e2e/member-management.spec.ts` |
| US-029 | Notification delivery baseline with inbox, email alerts, and preferences | yes | yes | yes | yes | implemented | `./scripts/verify-us-029.sh`; `frontend/e2e/notifications.spec.ts` |
| US-030 | User-scoped event watchlist, reminder scheduling, and watched-state filters | yes | yes | yes | yes | implemented | `./scripts/verify-us-030.sh`; `frontend/e2e/event-watchlist.spec.ts` |
| US-031 | Canonical event manual overrides, overwrite protection, and change history | yes | yes | yes | yes | implemented | `./scripts/verify-us-031.sh`; `frontend/e2e/event-overrides.spec.ts` |
| US-032 | Live external API/RSS/ICS discovery with policy-aware canonical event ingestion | yes | yes | yes | yes | implemented | `./scripts/verify-us-032.sh`; `frontend/e2e/live-feed-discovery.spec.ts` |
| US-033 | Public website Playwright discovery with policy-aware browser recipe extraction | yes | yes | yes | yes | implemented | `./scripts/verify-us-033.sh`; `frontend/e2e/website-playwright-discovery.spec.ts` |
| US-034 | Selenium or alternate-adapter discovery with engine-aware canonical event ingestion | yes | yes | yes | yes | implemented | `./scripts/verify-us-034.sh`; `frontend/e2e/selenium-website-discovery.spec.ts` |
| US-035 | Scheduled discovery runs with bounded recurrence and overlap-safe dispatch | yes | yes | yes | yes | implemented | `./scripts/verify-us-035.sh`; `frontend/e2e/discovery-schedule.spec.ts` |
| US-036 | Governed query expansion with approval-required AI suggestions | yes | yes | yes | yes | implemented | `./scripts/verify-us-036.sh`; `frontend/e2e/query-expansion.spec.ts` |
| US-037 | Discovery copilot with structured grounded recommendations | yes | yes | yes | yes | implemented | `./scripts/verify-us-037.sh`; `frontend/e2e/discovery-copilot.spec.ts` |
| US-038 | Governed AI feedback signals for discovery and audience outputs | yes | yes | yes | yes | implemented | `./scripts/verify-us-038.sh`; `frontend/e2e/ai-feedback.spec.ts` |
| US-039 | Governed feedback-learning scoring suggestions | yes | yes | yes | yes | implemented | `./scripts/verify-us-039.sh`; `frontend/e2e/scoring-suggestion.spec.ts` |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.
