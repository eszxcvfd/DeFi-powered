# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | Feedback validators enforce supported target types, state vocabularies, reason-code requirements, and no-auto-learning guardrails. |
| Integration | Feedback persistence stays tenant-scoped, preserves history plus effective-state projection, and serves both discovery-copilot and audience-hypothesis targets. |
| E2E | A user leaves feedback on a discovery-copilot response and an audience hypothesis, refreshes, and sees the effective state without the underlying AI artifact changing. |
| Platform | Story verify command keeps AI-feedback routes, UI flows, and Harness matrix evidence wired together. |

## Suggested Checks

- Backend unit tests for:
  - Discovery-copilot feedback state validation.
  - Audience-hypothesis feedback state validation.
  - Reason-code requirements for negative or uncertain feedback.
  - Projection logic that resolves the latest effective feedback state.
- Backend integration tests for:
  - Tenant-scoped feedback write/read behavior.
  - Updating feedback for the same user and target.
  - Rejection of cross-tenant or unsupported target references.
  - Audit-log emission or equivalent feedback trace behavior.
- Frontend/E2E coverage for:
  - Feedback controls in discovery-copilot UI.
  - Feedback controls in event-detail audience UI.
  - Persisted effective state after reload.
  - Safe messaging that feedback informs later review rather than immediate
    autonomous changes.

## Evidence Hooks

- `tests/unit/` feedback-validator and projection tests
- `tests/integration/` feedback API and scoping tests
- `frontend/e2e/` discovery-copilot and audience-feedback scenarios
- `scripts/verify-us-038.sh`

## Resolved (US-038 implementation)

- Negative discovery-copilot feedback requires a reason code; positive feedback
  keeps reason optional.
- Read surfaces expose the current viewer's effective feedback only (dev-header
  actors use `dev:{role}` keys).
- One shared governed reason-code vocabulary applies to both target types.
