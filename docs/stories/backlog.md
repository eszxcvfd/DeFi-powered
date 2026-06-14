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
| E03 Lead And Reporting | Lead pipeline, duplicate detection, activities, follow-up reminders, dashboard, funnel, source performance, export. | unsliced |
| E04 Browser-Assisted Operations | Headed browser session console, profile lifecycle, confirmation workflow, screenshots/traces, optional CloakBrowser adapter review. | unsliced |
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
