# Validation

## Proof Strategy

This story is done only when LiveLead can require preview and explicit
confirmation for destructive or external-side-effect browser actions, keep that
confirmation scoped to one requested action, and preserve explainable audit and
session state through confirm or cancel outcomes.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Action classification, preview consistency, confirmation scoping, token/state expiration, and cancel behavior. |
| Integration | Confirmation-required API responses, confirm/cancel transitions, blocked or expired requests, and audit-context persistence. |
| E2E | User requests a side-effect action, reviews the preview, confirms or cancels it, and sees the resulting session state and feedback. |
| Platform | Story verify command keeps confirmation-gated action flows, backend APIs, and browser-session UI feedback wired into the Harness matrix. |
| Performance | Preview generation and confirmation transitions remain responsive and do not leave stuck pending-confirmation state under normal local proof conditions. |
| Logs/Audit | Confirmation-gated browser actions remain diagnosable with request actor, preview summary, confirm/cancel decision, execution result, and session context. |

## Fixtures

- Seeded active session and connector policy that allows one confirmation-gated
  side-effect action.
- Deterministic preview or dry-run fixture for the target side-effect action.
- An expired, cancelled, or invalid confirmation fixture for negative-path proof.
- A blocked policy or unsafe side-effect fixture for safe-failure proof.

## Commands

```text
- ./scripts/verify-us-022.sh — planned story verification chain for confirmation-gated browser-action unit/integration coverage
- frontend/e2e/browser-confirmation-actions.spec.ts — planned browser proof for preview and confirm/cancel flows
```

## Acceptance Evidence

- `tests/unit/test_browser_action_confirmation.py` — classification, preview, and confirmation rules
- `tests/integration/test_browser_action_confirmation_api.py` — confirmation-required, confirm/cancel, and audit handling
- Browser session UI with preview and explicit confirm/cancel feedback
- `scripts/bin/harness-cli story verify US-022` — passes with `./scripts/verify-us-022.sh`
