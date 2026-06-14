# LiveLead Product Overview

Source: `SPEC.md` (`LLDE-SRS-001`, version 1.0.0, 2026-06-13).

## Product Summary

LiveLead is a web application for discovering livestreams, webinars, online
conferences, and hybrid events that may contain qualified leads. It helps users
define an ICP, discover permitted event sources, normalize event data, score
event priority, prepare engagement plans, and track leads through an internal
pipeline.

The product is not an autonomous sales bot. MVP behavior must keep public
posting, messaging, and other external actions under explicit human review and
confirmation.

## MVP Principles

- Value-first engagement: suggestions should help the audience before they ask
  for anything.
- Human-controlled actions: users review and approve generated content.
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

## Primary Users

| Role | Product Need |
| --- | --- |
| Owner/Admin | Configure organization, users, source policy, quotas, audit, and governance. |
| Analyst | Create campaigns, run discovery, review events, and produce reports. |
| Sales/BD | Save leads, use engagement plans, update pipeline state, and record outcomes. |
| Reviewer | Approve, reject, or revise AI-generated engagement content. |
| Viewer | Read dashboards, reports, and event details within granted permissions. |

## Core Product Domains

- Organization, user, tenant, role, and permission management.
- Campaign and ICP definition.
- Source registry, source policy, connector configuration, and secret handling.
- Discovery jobs, progress tracking, retry, cancellation, and scheduling.
- Event normalization, deduplication, provenance, and confidence.
- Event list/detail views, filtering, watchlist, and calendar/export workflows.
- Audience hypotheses, evidence links, scoring, and explainability.
- Engagement plans, generated content, approval workflow, and anti-spam rules.
- Browser-assisted sessions with policy enforcement and user confirmation.
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

## Non-Goals For MVP

- Autonomous public comments, mass messaging, or connection invites.
- CAPTCHA, MFA, bot challenge, paywall, or private-account bypass.
- Proxy rotation or evasion-oriented automation.
- Sensitive attribute inference or face recognition.
- Full enterprise CRM replacement.
- Revenue or conversion guarantees.
