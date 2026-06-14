# Validation

## Proof Strategy

This story is done only when LiveLead can prove a manual discovery run end to
end through deterministic mock connectors, including creation, progress,
terminal states, policy gates, cancellation, and cleanup behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Job state transitions, snapshot creation, retry classification, cancellation precedence, and partial-success aggregation. |
| Integration | API + queue + persistence tests for create/start/status/cancel flows, policy-denied start, progress persistence, and idempotent retry behavior. |
| E2E | Analyst launches a run from a campaign, sees progress updates, observes success/partial/failure fixture outcomes, and cancels a running job. |
| Platform | Story verify command keeps backend worker, frontend progress UI, and streaming transport checks wired into the Harness matrix. |
| Performance | Deterministic multi-source mock runs stay within bounded local concurrency and do not block the API process. |
| Logs/Audit | Lifecycle transitions, denied starts, cancellations, and cleanup are observable without leaking secrets or low-level connector internals. |

## Fixtures

- One valid campaign with saved criteria.
- At least three approved mock sources:
  - Success fixture source.
  - Partial/failure fixture source.
  - Policy-denied or needs-user-action fixture source.
- Deterministic progress payloads for pages processed, items found, and final
  outcome.
- A cancellable long-running mock source to prove cancellation and cleanup.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-004.sh
```

## Acceptance Evidence

- `./scripts/verify-us-004.sh` — lifecycle unit tests, API+mock worker integration, Playwright discovery-run e2e (API + dramatiq worker in e2e webServer).
