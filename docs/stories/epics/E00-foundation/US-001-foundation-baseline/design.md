# Design

## Domain Model

This story should avoid business domain schema. It may define placeholder
concept boundaries for `Organization`, `User`, `Role`, `TenantScope`,
`SourcePolicy`, and `AuditEvent` only to prevent later code from bypassing
them. The story may also introduce non-domain runtime types such as
`AppSettings`, `HealthStatus`, and `RuntimeComponentStatus`, but those should
live outside the domain layer.

## Application Flow

- Query: health/smoke checks return service status, version metadata, and
  minimal dependency readiness.
- Command: runtime bootstrap commands for worker start, migration bootstrap, and
  frontend build verification may exist, but no business mutation flow is added
  yet.
- Future business commands and queries must pass through auth, tenant, audit,
  and source-policy boundaries once those modules exist.

## Interface Contract

Minimum backend contract:

- `GET /health` or equivalent smoke endpoint.
- Stable JSON response suitable for local and CI checks.
- Typed settings bootstrap for SQLite path, Redis URL, and environment mode.

Minimum frontend contract:

- App shell renders without requiring real product data.
- Navigation labels can be placeholders for dashboard, campaigns, events,
  content, leads, browser session, and admin surfaces.
- The shell should visually prove the selected Vite + React + `shadcn/ui`
  baseline rather than a bare HTML placeholder.

## Data Model

No business tables should be created in this story unless the selected framework
requires migration infrastructure metadata. SQLite and Redis are local
infrastructure dependencies, not product data proof yet.

Expected persistence outputs for Foundation:

- SQLite file path configuration under the project, for example
  `data/livelead.sqlite3`.
- Alembic bootstrap and migration metadata.
- No campaign, event, lead, or connector business schema yet unless the story
  scope is explicitly expanded.

## UI / Platform Impact

The frontend should prove that the chosen UI stack runs locally and is ready to
consume backend contracts later. The backend and worker should prove they can
boot with SQLite and Redis configuration. None of this should imply that
dashboard or domain workflows are already implemented.

## Observability

The backend should establish a direction for request logging with request ID,
status code, duration, and message. It should also leave clear hook points for
OpenTelemetry instrumentation and Sentry error capture, even if full external
wiring is not activated in Foundation. Product audit records are not
implemented in this story but must remain a named boundary.

## Alternatives Considered

1. Start with the campaign workflow first. Rejected for now because the repo has
   no runnable stack or validation commands.
2. Build auth first. Deferred because production auth is high-risk and should
   follow after the scaffold proves local development and tests.
3. Keep `US-001` stack-agnostic. Rejected because the project has already
   accepted a concrete technology baseline in `0011`.
