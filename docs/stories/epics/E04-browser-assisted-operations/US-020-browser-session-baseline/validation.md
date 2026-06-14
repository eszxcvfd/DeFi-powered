# Validation

## Proof Strategy

This story is done only when LiveLead can open a supervised browser session from
an allowed event or source entrypoint, show live lifecycle status and runtime
context in the UI, and stop the session safely while preserving explainable
policy and audit context.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Session-state transitions, isolation metadata derivation, launch-context validation, and stop eligibility rules. |
| Integration | Policy-gated session creation, durable status reads, worker session startup and shutdown, and adapter cleanup behavior. |
| E2E | User launches a browser session from the UI, sees engine/state/URL/runtime updates, and stops the session safely. |
| Platform | Story verify command keeps browser-worker lifecycle, backend session APIs, and frontend session-console wiring in the Harness matrix. |
| Performance | Session start and stop remain responsive under realistic local worker conditions, and stop cleanup does not leave orphaned browser resources in normal proof runs. |
| Logs/Audit | Browser session requests remain diagnosable with actor, launch target, engine, policy result, state transitions, and stop outcome. |

## Fixtures

- Seeded source or event records that permit browser-session launch.
- Deterministic browser-worker or adapter fixture that can expose startup,
  running, and stopped states safely in local proof.
- A denied or invalid launch context fixture for policy-error proof.
- A session fixture that reaches a user-visible terminal state after stop.

## Commands

```text
- ./scripts/verify-us-020.sh — story verification chain (smoke-browser-worker + unit/integration + e2e)
- frontend/e2e/browser-session.spec.ts — browser proof for supervised session flows
```

## Acceptance Evidence

- `tests/unit/test_browser_session_lifecycle.py` — lifecycle, isolation, and stop rules
- `tests/integration/test_browser_sessions_api.py` — create/status/stop behavior and policy denial handling
- Browser session console UI with launch and stop feedback
- `scripts/bin/harness-cli story verify US-020` — pass when Playwright browsers are installed (`scripts/playwright-install.sh`)
