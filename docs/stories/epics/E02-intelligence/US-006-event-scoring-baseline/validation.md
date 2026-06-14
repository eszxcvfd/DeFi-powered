# Validation

## Proof Strategy

This story is done only when LiveLead can rank canonical events with a
campaign-aware score, expose an explainable breakdown, preserve score-version
metadata, and let users trigger an explicit re-score without losing review
context.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Score math, component weighting, threshold mapping, clamping to `[0,100]`, explanation assembly, and missing-data handling. |
| Integration | Score persistence, version metadata, event-list score summaries, event-detail score breakdown, and explicit re-score behavior. |
| E2E | Analyst or sales user opens reviewed events, sees ranked score badges, opens score detail, and triggers a re-score with updated output. |
| Platform | Story verify command keeps backend scoring, API detail behavior, and frontend score-review checks wired into the Harness matrix. |
| Performance | Score lookup stays responsive for deterministic local event sets and does not require synchronous full reprocessing on every list request. |
| Logs/Audit | Score calculations, score-version changes, and re-score actions remain diagnosable without leaking secrets or inventing unsupported evidence. |

## Fixtures

- One campaign with persisted scoring weights from `US-002`.
- At least one completed deterministic discovery run normalized into canonical
  events from `US-005`.
- Event fixtures with enough variation to produce multiple priority levels.
- A fixture with missing or low-confidence fields that should lower confidence
  or explain missing score inputs.
- A fixture pair showing a score change after campaign-weight or event-data
  updates.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-006.sh
```

## Acceptance Evidence

- `./scripts/verify-us-006.sh` (extends US-004 foundation path; unit + integration scoring tests).
- `tests/unit/test_scoring_calculator.py`, `tests/integration/test_events_scoring_api.py`.
- `frontend/e2e/event-scoring.spec.ts` (included in foundation `test:e2e`).
- Discovery worker normalizes mock findings to `events` and runs initial scoring when items are created.
