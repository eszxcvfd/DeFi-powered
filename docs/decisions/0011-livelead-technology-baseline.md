# 0011 LiveLead Technology Baseline

Date: 2026-06-13

## Status

Accepted

## Context

`SPEC.md` defined a preferred technology shortlist for the MVP, but `US-001`
needs a concrete implementation baseline so scaffolding, validation, and future
story work all target the same stack. Leaving backend, queue, frontend, UI, and
observability choices open would create drift between architecture documents,
story expectations, and eventual implementation.

## Decision

LiveLead adopts the following technology baseline for the current MVP
foundation:

| Layer | Selected Technology | Notes |
| --- | --- | --- |
| Backend | Python 3.12+, FastAPI, Pydantic | Async API, typed request/response schemas, straightforward boundary parsing |
| ORM | SQLAlchemy 2.x | Repository and persistence layer with async-friendly APIs |
| Migration | Alembic | Schema migration workflow aligned with SQLAlchemy |
| Database | SQLite | Project-local primary store, local-first, simple MVP operations |
| Queue | Dramatiq + Redis | Background jobs, retries, and operational simplicity over Celery complexity |
| Browser | Playwright Python | Default browser automation engine |
| Browser fallback | Selenium Python | Fallback for connectors that need WebDriver behavior |
| Optional Chromium | CloakBrowser adapter | Policy-gated, not part of the default runtime path |
| Frontend | React + TypeScript + Vite | Interactive app shell with simpler separation from the Python backend |
| UI components | shadcn/ui | Lightweight, composable, consistent design system baseline |
| AI | OpenAI-compatible provider abstraction | Adapter-first design; local model providers can be added behind the same interface |
| Testing | Pytest, Playwright E2E, Hypothesis | Unit, integration, E2E, and targeted property-based checks |
| Observability | OpenTelemetry, Prometheus, Grafana, Sentry | OpenTelemetry instrumentation, Sentry for errors, Prometheus/Grafana for metrics and dashboards |
| Packaging | Docker Compose for dev and single-host MVP | Kubernetes is explicitly out of the MVP baseline |

Additional selection rules:

- `Dramatiq` is the default queue framework; switching to `Celery` or `ARQ`
  requires a follow-up decision.
- `Vite` is the default frontend app framework; `Next.js` is not part of the
  current baseline.
- `shadcn/ui` is the single component-system baseline for the initial UI.
- `Sentry` is the default error-monitoring sink for MVP; Prometheus and Grafana
  are part of the preferred operational stack when runtime metrics are exposed.
- `Kubernetes` is not a packaging target for MVP unless a later decision
  expands the deployment scope.

## Alternatives Considered

1. Keep the shortlist open and defer concrete picks to implementation time.
   Rejected because `US-001` needs a stable baseline for scaffolding and proof.
2. Choose `Celery` as the default queue. Rejected because it adds more
   configuration surface than needed for the current MVP baseline.
3. Choose `Next.js` as the default frontend framework. Rejected because the
   product already has a dedicated Python backend and does not currently need a
   full-stack React framework baseline.
4. Choose `Material UI` or `Ant Design` as the default component system.
   Rejected because the project benefits more from a lighter, composable UI
   layer at this stage.

## Consequences

Positive:

- `US-001` can scaffold against concrete runtime, frontend, queue, and testing
  choices.
- The architecture and product contract can stop treating these stack choices
  as unresolved.
- Future decisions can focus on auth, storage operations, or deployment scope
  instead of re-litigating the whole baseline.

Tradeoffs:

- The project is now more opinionated about queueing, UI tooling, and frontend
  packaging.
- A future shift to `Celery`, `Next.js`, or another UI system becomes an
  explicit architecture change rather than an implementation detail.
- The observability toolchain is broader than what local-only development may
  use immediately.

## Follow-Up

- Update `docs/ARCHITECTURE.md` and product contract docs to reference this
  baseline directly.
- Implement the selected stack in `US-001`.
- Record new decisions if auth/SSO, object storage provider, or deployment
  scope change materially.
