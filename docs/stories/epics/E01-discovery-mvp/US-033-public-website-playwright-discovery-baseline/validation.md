# Validation

## Proof Strategy

This story is done only when LiveLead can run approved public-website
`Playwright` discovery connectors inside a manual discovery job, safely extract
reviewable event evidence into canonical records, and stop cleanly on policy or
challenge barriers without leaking secrets or widening into uncontrolled browser
automation.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Recipe validation, locator-strategy rules, pagination/scroll budget enforcement, and challenge-safe state mapping. |
| Integration | Fixture-site browser discovery through the shared `Playwright` adapter, policy deny before execution, extraction mapping, canonical event persistence, and secret-safe diagnostics. |
| E2E | Analyst launches a manual discovery run that includes an approved public website connector, sees per-source progress/outcomes, and reviews canonical events created from website extraction. |
| Platform | Story verification command proves browser-worker plus `Playwright` adapter fixtures open/close cleanly and stay wired into existing discovery-job proof paths. |
| Performance | Website discovery respects configured page/time budgets and does not keep worker/browser processes alive after terminal outcome. |
| Logs/Audit | Policy block, timeout, challenge detection, and extraction-failure paths remain explainable with source id, connector type, job id, and redacted diagnostics. |

## Fixtures

- At least one campaign with an approved public website connector enabled.
- One local fixture site or deterministic public-website test surface for
  `Playwright` discovery.
- One blocked or incomplete website connector to prove readiness/policy deny
  behavior.
- One fixture page that simulates timeout, unstable DOM, or challenge barrier
  to prove safe-stop handling.
- Canonical event assertions that confirm website findings reach the existing
  event review pipeline.

## Commands

```text
./scripts/verify-us-033.sh
./scripts/bin/harness-cli story verify US-033
```

Proof includes:

- unit tests for browser recipe validation and challenge-safe state mapping
- integration tests for fixture-site `Playwright` discovery and canonical event
  ingestion
- frontend e2e `website-playwright-discovery.spec.ts` for discovery progress and
  website-derived event review

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-033` once implemented with
  the expected proof columns populated.
- A representative integration or e2e run shows at least one approved website
  connector producing canonical event review data through the `Playwright`
  adapter.
- Proof shows challenge or blocked website sources stop safely and do not
  silently escalate into login, saved-state reuse, or external-side-effect
  flows.
