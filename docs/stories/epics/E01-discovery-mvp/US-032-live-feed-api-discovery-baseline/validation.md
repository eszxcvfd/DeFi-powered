# Validation

## Proof Strategy

This story is done only when LiveLead can run approved live external
`API`/`RSS`/`ICS` connectors from a manual discovery job, safely persist the
resulting canonical event evidence, and surface blocked or partial outcomes
without leaking secrets or silently falling back to browser automation.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Source-readiness rules, parser mapping, stable-identity extraction, safe-stop transitions, and live-source provenance shaping. |
| Integration | Fixture-backed feed/API fetch, policy deny before execution, partial-success multi-source runs, canonical event persistence, and secret redaction in job/admin responses. |
| E2E | Analyst launches a manual discovery run against approved live sources, sees per-source progress/outcomes, and reviews canonical events created from live-source results. |
| Platform | Story verification command proves worker, API, and frontend live-source fixtures succeed without weakening existing discovery-job or event-review proof paths. |
| Performance | Live-source fetch and normalization remain bounded for configured page/time budgets and do not block the rest of the discovery job indefinitely. |
| Logs/Audit | Denied source, quota-blocked source, parse failure, and needs-user-action paths remain explainable with source id, connector type, job id, and redacted diagnostics. |

## Fixtures

- At least one campaign with approved live feed/API sources enabled.
- One approved live source fixture that returns event items through `API`,
  `RSS`, `Atom`, `sitemap`, or `ICS` shape.
- One denied or over-quota source to prove safe block behavior.
- One live source fixture that simulates auth challenge or interactive barrier
  to prove `NEEDS_USER_ACTION` or denied handling.
- Canonical event fixtures or assertions that confirm live items reach the
  existing event review pipeline.

## Commands

```text
./scripts/verify-us-032.sh
```

- unit tests for live-source readiness and parser mapping
- integration tests for fixture-backed feed/API discovery and canonical event
  ingestion
- `frontend/e2e/live-feed-discovery.spec.ts` for live discovery progress and
  reviewable event results
- `scripts/bin/harness-cli story verify US-032`

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-032` once implemented with
  the expected proof columns populated.
- A representative integration or e2e run shows at least one approved live
  source producing canonical event review data.
- Proof shows denied or interactive sources stop safely and do not silently
  trigger browser automation.
