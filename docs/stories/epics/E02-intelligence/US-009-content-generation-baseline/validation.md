# Validation

## Proof Strategy

This story is done only when LiveLead can generate persisted draft variants
from event and engagement-plan context, show generation metadata and risk
flags, and let users edit drafts without implying approval or external sending.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Generation-request validation, context assembly, risk-flag rules, metadata mapping, and inline-edit attribution updates. |
| Integration | Draft persistence, `POST /content/generate`, metadata storage, risk-flag persistence, and event-linked draft retrieval. |
| E2E | Analyst or sales user opens content generation, reviews context, creates draft variants, and edits at least one draft. |
| Platform | Story verify command keeps backend generation, API payload behavior, and frontend content-studio checks wired into the Harness matrix. |
| Performance | Draft generation and retrieval stay responsive for deterministic local fixtures and avoid unnecessary full regeneration on every view. |
| Logs/Audit | Generation requests, provider failures, draft creation, and draft edits remain diagnosable without leaking provider secrets or implying approval. |

## Fixtures

- One event with engagement plan, score, and audience context rich enough to
  generate multiple draft variants.
- Settings fixtures spanning at least two platforms and two content types.
- Negative fixtures that should trigger spam, unsupported-claim, or
  sensitive-targeting warnings.
- A persisted draft fixture that demonstrates inline editing and attribution.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-009.sh
```

## Acceptance Evidence

- `./scripts/verify-us-009.sh` — pytest `test_content_risk`, `test_content_api`.
- Playwright: `frontend/e2e/content-generation.spec.ts`.
