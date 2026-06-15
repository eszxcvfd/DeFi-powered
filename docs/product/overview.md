# LiveLead Product Overview

Source: `SPEC.md` (`LLDE-SRS-001`, version 1.1.0, 2026-06-14), plus
`docs/product/mvp-scope-and-priorities.md`.

## Product Summary

LiveLead is a web application for discovering livestreams, webinars, online
conferences, and hybrid events that may contain qualified leads, then helping a
human operator decide how to interact around those events to open legitimate
business conversations. The MVP stays centered on seven user jobs: define a
market-search brief and ICP, discover permitted event sources, normalize and
deduplicate event data, score event priority, prepare engagement playbooks,
suggest human-reviewed interaction content, and track leads through an internal
pipeline.

The product is not an autonomous sales bot. MVP behavior must keep public
posting, messaging, and other external actions under explicit human review and
confirmation.

The current product contract also assumes:

- users may begin with a natural-language GenAI brief
- interaction planning must support `UPCOMING`, `LIVE`, and `ENDED` event
  states
- channel strategy can span LinkedIn, Facebook, X, email, Instagram, YouTube,
  TikTok, Pinterest, Threads, forums, Discord, website/blog, and other allowed
  sources
- the product supports an intermediary business model that opens opportunities
  for partner companies instead of assuming direct service delivery
- target-market focus can be weighted by region

## Scope Hierarchy

The current source of truth for MVP scope prioritization is
`docs/product/mvp-scope-and-priorities.md`.

LiveLead's seven core jobs are:

1. Receive market-search intent, natural-language discovery questions, and
   ideal customer profile inputs.
2. Discover events from permitted sources.
3. Normalize, deduplicate, and classify event state.
4. Analyze audience signals and score event priority.
5. Create engagement plans before, during, and after the event, by phase and
   by channel.
6. Suggest comments, questions, messages, email, and follow-up content for
   human review.
7. Save leads, activities, stages, and outcomes in the internal pipeline.

Browser governance, operator tooling, and reporting remain supporting
capabilities unless a later product decision explicitly raises them above one of
the seven jobs above.

## MVP Principles

- Value-first engagement: suggestions should help the audience before they ask
  for anything.
- Human-controlled actions: users review and approve generated content.
- Intermediary-first positioning: LiveLead helps open qualified conversations
  and partner introductions instead of assuming direct service fulfillment.
- Market-aware planning: campaigns and discovery can prioritize regions and
  market mix intentionally.
- State-aware playbooks: recommendations should differ for `UPCOMING`, `LIVE`,
  and `ENDED` events.
- Compliance by design: no CAPTCHA bypass, MFA bypass, access-control evasion,
  spam, or private-data scraping.
- Source-aware data: event records include source URL, observation time, and
  confidence.
- Explainable scoring: event scores expose components and reasons.
- Replaceable automation: Playwright, Selenium, and optional Chromium engines
  sit behind adapter interfaces.
- Privacy minimization: store only data needed for legitimate business use.
- Auditability: discovery, lead changes, AI generation, approvals, and sensitive
  automation actions are traceable.

## Supporting Capabilities

These capabilities support the seven jobs above and should not become the
primary product promise on their own:

- Source policy, approvals, quotas, and secret handling.
- Supervised browser-assisted access when feeds or official APIs are not
  sufficient.
- Browser confirmation, debug artifacts, profile lifecycle, and optional-engine
  governance.
- Reporting, export, audit, and operator visibility.

## Primary Users

| Role | Product Need |
| --- | --- |
| Owner/Admin | Configure organization, users, source policy, quotas, audit, and governance. |
| Analyst | Create campaigns, run discovery, review events, and produce reports. |
| Sales/BD | Save leads, use engagement plans, execute approved interactions, update pipeline state, and record outcomes. |
| Reviewer | Approve, reject, or revise AI-generated engagement content. |
| Viewer | Read dashboards, reports, and event details within granted permissions. |

## Core Product Domains

- Organization, user, tenant, role, and permission management.
- Campaign and ICP definition, including natural-language brief parsing,
  business model, and target-market weighting.
- Source registry, source policy, connector configuration, multi-channel
  coverage, and secret handling.
- Discovery jobs, progress tracking, retry, cancellation, scheduling, and
  structured discovery assumptions.
- Event normalization, deduplication, provenance, and confidence.
- Event list/detail views, filtering, watchlist, and calendar/export workflows.
- Audience hypotheses, evidence links, scoring, and explainability.
- Engagement plans, generated content, approval workflow, intermediary framing,
  and anti-spam rules.
- Browser-assisted sessions with policy enforcement and user confirmation as a
  supporting access path, not a separate primary workflow.
- Lead pipeline, activities, reminders, import/export, reporting, and audit.

## Implementation Status

- **US-001 (Foundation):** Runnable FastAPI API (`GET /health`), Vite + React app shell,
  SQLite path + Alembic bootstrap, Dramatiq + Redis worker wiring, and
  `docs/FOUNDATION_RUNTIME.md`.
- **US-002 (Campaign ICP):** Campaign CRUD API, SQLite persistence, wizard + list UI;
  scoring weights persist.
- **US-003 (Source policy):** Connector registry, policy evaluation, encrypted secrets,
  `/admin/connectors`, wizard source step.
- **US-004 (Discovery jobs):** Manual run via mock connectors, Dramatiq worker, progress/cancel/SSE;
  campaign detail Run discovery.
- **US-005 (Event results):** Canonical event persistence, provenance-aware deduplication,
  results list/detail UI, and source evidence review.
- **US-006 (Event scoring):** Campaign-aware event scoring, score breakdown, explicit
  re-score behavior, and priority surfacing in event review.
- **US-007 (Audience hypotheses):** Explainable audience hypotheses, evidence links,
  confidence signaling, and sensitive-inference guardrails in event detail.
- **US-008 (Engagement plans):** Phase-based engagement plans, task tracking, and
  anti-spam planning guardrails before content generation.
- **US-009 (Generated content):** Draft variants, provider metadata, inline editing,
  and safety flags in the first content-studio slice.
- **US-010 (Content approval):** Reviewer approval and rejection workflow with
  explicit review states and decision history.
- **US-011 (Content handoff):** Approved-only copy/export flow, explicit
  used-state transition, and handoff audit metadata before send workflows.
- **US-012 (Lead pipeline):** Event-linked and manual lead creation, default
  pipeline stages, duplicate guardrails, activity history, and table/Kanban UI.
- **US-013 (Follow-up reminders):** Lead-linked reminders from follow-up dates,
  due/overdue queue, complete/reschedule, in-app banner, and pipeline cues.
- **US-014 to US-019 (Reporting and outcomes):** Dashboard overview, lead
  outcomes, funnel reporting, source-performance reporting,
  content-effectiveness reporting, and report export extend the core lead and
  pipeline jobs rather than adding a new product direction.
- **US-020 to US-025 (Supporting browser governance):** Supervised browser
  session launch, read-only actions, explicit confirmation, debug artifacts,
  profile lifecycle, and CloakBrowser approval gates deepen the governed
  browser-assist capability. These stories support core discovery and
  human-reviewed outreach flows; they do not redefine LiveLead as a browser
  automation platform.

## Non-Goals For MVP

- Autonomous public comments, mass messaging, or connection invites.
- Broad autonomous posting flows across any supported channel.
- CAPTCHA, MFA, bot challenge, paywall, or private-account bypass.
- Proxy rotation or evasion-oriented automation.
- Sensitive attribute inference or face recognition.
- Full enterprise CRM replacement.
- Revenue or conversion guarantees.
- Turning browser governance into the main product value path instead of a
  supporting capability.
