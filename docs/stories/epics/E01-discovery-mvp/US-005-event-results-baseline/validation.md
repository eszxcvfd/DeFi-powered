# Validation

## Proof Strategy

This story is done only when LiveLead can turn deterministic discovery output
into canonical, reviewable events with preserved provenance, explainable
deduplication, and a user-visible results list/detail flow.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Normalization mapping, required source-field preservation, confidence tagging, deduplication heuristics, and merge-decision explanation rules. |
| Integration | Persistence for canonical events and source observations, campaign/event list queries, event detail queries, and repeated-findings merge behavior. |
| E2E | Analyst completes a deterministic discovery run, opens event results, filters the list, and reviews event detail source evidence. |
| Platform | Story verify command keeps backend normalization, API review endpoints, and frontend event-review checks wired into the Harness matrix. |
| Performance | Event review stays responsive for deterministic local runs with repeated observations and does not require synchronous reprocessing on every list request. |
| Logs/Audit | Merge decisions, source-evidence availability, and redaction behavior are diagnosable without leaking secrets or raw credentials. |

## Fixtures

- One campaign with at least one completed deterministic discovery run.
- At least two approved mock sources that can emit overlapping event findings.
- A duplicate-event fixture that should merge into one canonical record.
- A near-duplicate fixture that should remain separate.
- Provenance fixtures with different observation timestamps and source URLs.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-005.sh
```

## Acceptance Evidence

- `./scripts/verify-us-005.sh` (extends US-004; unit dedup/confidence + integration merge/provenance).
- `tests/unit/test_event_deduplication.py`, `tests/unit/test_event_confidence.py`, `tests/integration/test_events_review_api.py`.
- `frontend/e2e/event-review.spec.ts` (discovery → list filter → detail provenance/evidence).
- Worker ingest uses `ingest_finding` with explainable merge logging.
