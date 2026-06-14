# Validation

## Proof Strategy

This story is done only when LiveLead can show explainable audience hypotheses
for canonical scored events, preserve evidence or labeled inference, and keep
sensitive-inference guardrails visible and testable.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Hypothesis generation rules, confidence mapping, evidence labeling, safe empty-state behavior, and sensitive-inference blocking. |
| Integration | Audience persistence, event-detail audience payloads, generation metadata, and unavailable-analysis handling. |
| E2E | Analyst or sales user opens scored event detail, reviews audience hypotheses, and sees evidence or inference labels. |
| Platform | Story verify command keeps backend audience generation, API detail behavior, and frontend audience-review checks wired into the Harness matrix. |
| Performance | Audience lookups stay responsive for deterministic local event sets and do not require synchronous heavy recomputation on every detail view. |
| Logs/Audit | Audience-generation runs, evidence labeling, and blocked sensitive outputs remain diagnosable without leaking protected or secret data. |

## Fixtures

- One scored event with rich event metadata and source observations.
- One scored event with sparse metadata that should produce a safe empty or
  low-confidence result.
- Evidence fixtures tying hypotheses to organizer, speaker, topic, sponsor, or
  tag cues.
- Negative fixtures that would tempt sensitive-attribute inference and must be
  rejected or ignored.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-007.sh
```

## Acceptance Evidence

- `./scripts/verify-us-007.sh` (extends US-006 path).
- `tests/unit/test_audience_generator.py`, `tests/integration/test_audience_api.py`.
- `frontend/e2e/audience-hypothesis.spec.ts`.
- `GET /events/{id}` includes `audience`; `POST /events/{id}/audience/refresh`.
