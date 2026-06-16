# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | Environment-profile, live-toggle, readiness, and rollback-state rules fail closed for missing auth hardening, missing dependencies, or unsafe live enablement. |
| Integration | Runtime configuration, health/readiness routes, backup metadata, and protected runtime-readiness surfaces work against the accepted single-host stack. |
| E2E | In the pilot-live environment, an authenticated operator can sign in, access a campaign, run governed discovery, review events, use one AI-assisted flow, and complete one safe browser or notification path. |
| Security | Dev headers are disabled, secrets stay redacted, TLS assumptions are documented/enforced, browser-worker isolation remains intact, and live connector kill switches can freeze risky activity. |
| Operational | Go-live checklist, rollback checklist, backup evidence, restore rehearsal or equivalent proof, and post-cutover smoke/UAT results are documented and reviewable. |
| Platform | Story verify command keeps cutover evidence, runtime readiness, and Harness matrix proof wired together. |

## Suggested Checks

- Backend unit tests for:
  - Environment profile and launch-gate evaluation.
  - Readiness blocker vs warning classification.
  - Live integration toggle safety rules.
  - Pause/rollback state handling.
- Backend integration tests for:
  - `GET /health/live`
  - `GET /health/ready`
  - Protected `GET /admin/runtime-readiness`
  - Backup metadata persistence and freshness checks.
- Operational smoke/UAT checks for:
  - Sign in with real auth boundary.
  - Campaign load and save.
  - Discovery using at least one live-approved connector.
  - Event review and score visibility.
  - One AI-assisted generation path.
  - One governed browser or notification path.
  - Pause-live or rollback drill.

## Evidence Hooks

- `tests/unit/` runtime-readiness and launch-gate tests
- `tests/integration/` health, readiness, and admin runtime status tests
- `frontend/e2e/` pilot-live smoke flows
- `scripts/verify-us-040.sh`
- runbook/checklist docs for cutover, pause, rollback, and restore

## Open Questions

- Is the first pilot-live environment limited to one organization/workspace at
  launch, or should the initial cutover support multiple tenant workspaces
  immediately?
- Which live connectors are mandatory for go-live day one: feed/API only, or
  also one approved browser-discovery connector?
- Should runtime live-mode entry be controlled only by documented ops steps, or
  does the team want a first owner/admin UI/API control in this same slice?
