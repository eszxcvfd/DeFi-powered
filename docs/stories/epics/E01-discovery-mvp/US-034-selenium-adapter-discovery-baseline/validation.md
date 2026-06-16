# Validation

## Proof Strategy

This story is done only when LiveLead can run approved `Selenium`/alternate-
adapter discovery connectors inside a manual discovery job, safely extract
reviewable event evidence into canonical records, and stop cleanly on policy or
challenge barriers while preserving the shared browser-adapter contract.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Engine-selection rules, alternate-adapter eligibility, shared recipe validation, and challenge-safe state mapping. |
| Integration | Fixture-site discovery through the shared `Selenium`/alternate adapter interface, policy deny before execution, extraction mapping, canonical event persistence, and secret-safe diagnostics. |
| E2E | Analyst launches a manual discovery run that includes an approved alternate-adapter connector, sees per-source progress/outcomes, and reviews canonical events created from the extracted results. |
| Platform | Story verification command proves the `Selenium` adapter completes a read-only sample flow through the common interface and cleans up driver/session resources after terminal outcome. |
| Performance | Alternate-adapter discovery respects configured page/time budgets and does not keep worker/driver processes alive after terminal outcome. |
| Logs/Audit | Policy block, driver failure, timeout, and challenge detection paths remain explainable with source id, engine family, connector type, job id, and redacted diagnostics. |

## Fixtures

- At least one campaign with an approved `Selenium`/alternate-adapter connector
  enabled.
- One local fixture site or deterministic test surface for alternate-adapter
  discovery.
- One blocked or incomplete connector to prove readiness/policy deny behavior.
- One fixture page that simulates timeout, unstable DOM, or challenge barrier
  to prove safe-stop handling.
- Canonical event assertions that confirm alternate-adapter findings reach the
  existing event review pipeline.

## Commands

```text
./scripts/verify-us-034.sh
./scripts/bin/harness-cli story verify US-034
```

Proof includes:

- unit tests for engine selection and shared recipe validation
- integration tests for fixture-site `Selenium`/alternate-adapter discovery and
  canonical event ingestion
- one frontend e2e scenario for mixed-engine discovery progress and reviewable
  event results
- `scripts/bin/harness-cli story verify US-034` after a verification command is
  added

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-034` once implemented with
  the expected proof columns populated.
- A representative integration or e2e run shows at least one approved
  alternate-adapter connector producing canonical event review data.
- Proof shows the common interface can run a read-only sample flow through the
  `Selenium` adapter and stop safely without widening into login or
  external-side-effect flows.
