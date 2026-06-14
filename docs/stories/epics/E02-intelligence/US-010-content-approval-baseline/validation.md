# Validation

## Proof Strategy

This story is done only when LiveLead can move generated drafts through explicit
review states, preserve reviewer decisions and notes, and keep approved content
distinct from ordinary drafts without implying export or sending.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Review-state transitions, invalid-transition blocking, reviewer-note rules, and authorized versus unauthorized actions. |
| Integration | Approve/reject persistence, decision-history storage, status retrieval, and API error behavior. |
| E2E | Reviewer or equivalent user opens a draft, approves or rejects it, and sees updated status and review history in the UI. |
| Platform | Story verify command keeps backend approval workflow, API review behavior, and frontend content-review checks wired into the Harness matrix. |
| Performance | Review-state retrieval and decision writes stay responsive for local draft sets and do not require full draft regeneration. |
| Logs/Audit | Submit-for-review, approve, and reject actions remain diagnosable with actor, timestamp, and draft revision context. |

## Fixtures

- One generated-draft fixture in `DRAFT` state ready for review.
- One draft fixture in `IN_REVIEW` state.
- One approve-path fixture and one reject-path fixture with reviewer notes.
- Negative fixtures for unauthorized reviewer action and invalid transitions.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-010.sh
```

## Acceptance Evidence

- `./scripts/verify-us-010.sh`
- Playwright: `frontend/e2e/content-approval.spec.ts`.
