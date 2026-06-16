# Real Environment Cutover And Live Operations

Source: `SPEC.md` sections 2.4, 3.2, 3.3, 10, 11, 14, and 15.

## Product Goal

LiveLead needs a first real-environment operating contract so the current
test-oriented MVP can be cut over to a live operator environment quickly while
still keeping authentication, policy, backup, rollback, and connector safety
under control. The goal of this slice is not full enterprise production scale;
it is a governed single-host or small-footprint pilot environment that can run
real campaigns, real connectors, real browser sessions, and real operator
workflows safely enough to support immediate business use.

## MVP Scope

This product slice covers:

- One real operator environment with the accepted modular-monolith processes:
  `web-api`, `worker`, `scheduler`, `browser-worker`, `frontend`, `redis`, and
  persistent business storage.
- Runtime configuration that separates test defaults from live settings, with
  development headers disabled, real secrets provisioned, and live external
  integrations enabled only through explicit configuration.
- TLS-terminated application access, persistent database and artifact storage,
  daily backups, and a documented rollback path.
- Feature-flag or policy-gated rollout for live connectors, browser automation,
  AI providers, notifications, and risky external actions.
- Minimal health, readiness, smoke, and post-cutover verification checks for
  API, worker, scheduler, browser-worker, auth, discovery, AI, and notifications.
- Operator-facing visibility into connector health, last backup age, critical
  runtime warnings, and kill-switch state.
- A first production-like runbook for go-live, rollback, incident pause, and
  post-cutover verification.

This product slice does not yet cover:

- Multi-region deployment, blue/green routing, or zero-downtime traffic
  switching.
- Kubernetes or a distributed microservice control plane.
- Automatic horizontal autoscaling.
- A generalized enterprise secret-management procurement program beyond the
  first approved secret path.
- Broad cost-optimization or high-volume performance tuning beyond the first
  real-environment guardrails.

## Contract Rules

- Real-environment access must use the authenticated session boundary, not
  development actor headers.
- Live connectors, live AI providers, live notifications, and browser-assisted
  external actions must remain disabled by default until the environment profile
  explicitly enables them.
- Every live connector must retain policy metadata, approval scope, rate limit,
  retention rule, and kill-switch controls before being enabled in the real
  environment.
- Real-environment secrets, cookies, and saved browser-state material must be
  encrypted at rest and must never appear in logs or admin read surfaces.
- SQLite remains acceptable for the first live pilot only if daily backup,
  restore rehearsal, file locking expectations, and disk-capacity monitoring are
  part of the runtime contract.
- Browser-worker runtime must remain sandboxed, least-privilege, and separately
  stoppable without taking down the whole application.
- Cutover is incomplete until smoke/UAT checks pass for login, campaign access,
  discovery, event review, scoring, content generation, and at least one
  governed browser flow.
- Rollback must be documented and executable with bounded operator steps,
  including how to freeze new jobs, disable live connectors, restore data if
  needed, and surface degraded mode to users.
- Urgency does not waive policy: CAPTCHA bypass, MFA bypass, bulk send, secret
  leakage, and unsupported external automation remain forbidden in the live
  environment.

## Runtime And Admin Surface

- `GET /health/live`: confirms the API process is running.
- `GET /health/ready`: confirms database writability, Redis reachability,
  recent worker heartbeat, and required runtime configuration for the current
  environment profile.
- `GET /admin/runtime-readiness`: returns environment profile, critical feature
  flags, live-connector enablement state, last backup status, and outstanding
  blocking warnings for authorized operators.
- Existing admin connector, audit, browser-profile, and notification surfaces
  remain the control points for live enablement; this slice adds the first
  environment-readiness contract around them rather than replacing them.

## UI / Ops Surface

- Settings should expose a bounded runtime-readiness or launch panel for
  Owners/Admins.
- Operators should see whether the environment is in `test-like`, `pilot-live`,
  or `paused` mode.
- Critical warnings should be visible for missing TLS, stale backups, failed
  worker heartbeat, disabled auth hardening, or connectors left in an unsafe
  state.
- The first live runbook may be partly documentation-driven, but its status
  checkpoints should be reviewable from the product or adjacent operational
  surfaces.

## Validation Implications

- Unit proof should cover environment-profile evaluation, feature-gate rules,
  readiness checks, and rollback-state validation.
- Integration proof should cover live configuration loading, health/readiness
  behavior, backup metadata recording, and protected admin runtime-readiness
  access.
- E2E proof should cover authenticated sign-in, discovery with a live-approved
  connector path, event review, AI-assisted flow, and one governed browser or
  notification path in the cutover environment.
- Security proof should cover disabled dev headers, TLS assumptions, secret-safe
  logging, backup protection, connector kill-switch behavior, and sandboxed
  browser-worker runtime.
- Operational proof should include a documented go-live checklist, a rollback
  checklist, and one restore rehearsal or equivalent evidence before the
  environment is treated as live-ready.
