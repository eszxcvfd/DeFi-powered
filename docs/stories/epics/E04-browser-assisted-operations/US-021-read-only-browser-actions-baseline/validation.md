# Validation

## Proof Strategy

This story is done only when LiveLead can execute allowed read-only browser
actions inside an active supervised session, show action lifecycle updates in
the UI, and enforce selector and timeout or budget guardrails without widening
into destructive confirmation behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Action allowlist checks, read-only classification, selector-strategy preference, and timeout or budget rules. |
| Integration | Action execution through the shared browser interface, action-status persistence, blocked-policy handling, and challenge to `NEEDS_USER_ACTION` behavior. |
| E2E | User launches a session, runs supported read-only actions, and sees action lifecycle feedback and safe blocked states in the UI. |
| Platform | Story verify command keeps browser-worker action execution, backend action APIs, and session-console controls wired into the Harness matrix. |
| Performance | Supported read-only actions complete within expected local limits and stop safely when timeout or budget thresholds are hit. |
| Logs/Audit | Browser action requests remain diagnosable with actor, action type, allowlist result, selector mode, timeout or budget outcome, and final lifecycle state. |

## Fixtures

- Seeded active browser session records with supported connector policy.
- Deterministic browser-worker or adapter fixture for navigate, scroll, open
  detail, and read-text actions.
- A blocked action fixture to prove allowlist enforcement.
- A challenge or timeout fixture that reaches `NEEDS_USER_ACTION` or safe
  failure without bypass behavior.

## Commands

```text
- ./scripts/verify-us-021.sh — planned story verification chain for read-only browser-action unit/integration coverage
- frontend/e2e/browser-read-only-actions.spec.ts — planned browser proof for supervised action flows
```

## Acceptance Evidence

- `tests/unit/test_browser_action_policy.py` — allowlist, selector, and timeout rules
- `tests/integration/test_browser_session_actions_api.py` — action execution, blocked-policy, and needs-user-action handling
- Browser session UI with read-only action controls and lifecycle feedback
- `scripts/bin/harness-cli story verify US-021` — pass after the verify command is added
