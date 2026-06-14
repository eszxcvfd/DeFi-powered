# 0009 LiveLead Architecture Boundaries

Date: 2026-06-13

## Status

Accepted

## Context

`SPEC.md` defines a system that mixes tenant-scoped product data, source policy,
browser automation, AI-assisted content generation, audit requirements, and
user-facing web workflows. Before `US-001` scaffolds code, the project needs a
durable architecture record that names the system shape, module boundaries, and
non-negotiable enforcement points.

## Decision

LiveLead will use a modular monolith as the MVP architecture baseline, with
isolated processes for `web-api`, `worker`, `scheduler`, `browser-worker`, and
`frontend`, backed by a project-local SQLite primary store, Redis, and object
storage.

The architecture must preserve these boundaries:

- Domain and application logic remain independent from FastAPI, SQLAlchemy,
  Playwright, Selenium, Redis, and AI vendor SDKs.
- Runtime entrypoints such as `web-api`, `worker`, `scheduler`, and
  `browser-worker` stay outside domain and application layers, acting only as
  process wiring and interface composition.
- SQLite is the source of truth for product records; Redis is operational
  state; object storage is for large artifacts.
- Browser automation and AI integrations sit behind adapter abstractions and
  must not be imported directly by business logic.
- Tenant scope, RBAC, and audit enforcement happen in backend commands and
  queries, not only in the UI.
- Source policy is checked before connector execution, with official API and
  feed sources preferred over browser automation.
- CAPTCHA, MFA, bot challenges, and external posting actions require safe-stop
  behavior and human confirmation flows.

`docs/ARCHITECTURE.md` is the working architecture guide that expands this
decision into module topology, validation expectations, and open choices.

## Alternatives Considered

1. Start with microservices for discovery, scoring, engagement, and leads.
   Rejected because MVP needs faster coordination and simpler deployment.
2. Use a generic web app layout with direct provider calls from feature code.
   Rejected because browser, AI, and policy integrations need replaceable
   boundaries and stricter compliance controls.

## Consequences

Positive:

- `US-001` can scaffold with clear module ownership and fewer architectural
  ambiguities.
- Future stories inherit explicit rules for storage, automation, and audit.
- The team has a durable record for why adapters, tenant enforcement, and audit
  cannot be treated as optional polish.

Tradeoffs:

- Some technology choices remain open until Foundation implementation work.
- The modular monolith will require discipline to avoid leaking infrastructure
  concerns into domain code.

## Follow-Up

- Implement the selected queue framework, frontend framework, and UI baseline
  from `docs/decisions/0011-livelead-technology-baseline.md`.
- Finalize the authentication mechanism in `US-001` or the next directly
  affected story.
- Record new decisions if object storage, CloakBrowser approval, or audit
  retention policy become fixed.
