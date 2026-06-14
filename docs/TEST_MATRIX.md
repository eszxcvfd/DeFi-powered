# Test Matrix

This file maps product behavior to proof.

No product behavior has been defined or implemented yet. Do not mark a row
implemented until tests or validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Foundation runtime boots (API, SQLite path, worker wiring, frontend shell) | yes | yes | yes | yes | implemented | `./scripts/verify-foundation.sh` |
| US-002 | Campaign + ICP API/UI contract, org scope, scoring weights persist | yes | yes | yes | yes | implemented | `./scripts/verify-us-002.sh` |
| US-003 | Source registry, policy deny/runnable, admin UI, encrypted secrets | yes | yes | yes | yes | implemented | `./scripts/verify-us-003.sh` |
| US-004 | Manual discovery jobs, mock connectors, progress, cancel, SSE | yes | yes | yes | yes | implemented | `./scripts/verify-us-004.sh` |
| US-005 | Canonical event review list/detail, provenance, confidence, deduplication | yes | yes | yes | yes | implemented | `./scripts/verify-us-005.sh` |
| US-006 | Campaign-aware event scoring, priority breakdown, explicit re-score | yes | yes | yes | yes | implemented | `./scripts/verify-us-006.sh` |
| US-007 | Audience hypotheses, evidence links, confidence, sensitive-inference guardrails | yes | yes | yes | yes | implemented | `./scripts/verify-us-007.sh` |
| US-008 | Engagement plans, phased tasks, task-state updates, anti-spam planning guardrails | yes | yes | yes | yes | implemented | `./scripts/verify-us-008.sh`; engagement API + `frontend/e2e/engagement-plan.spec.ts` |
| US-009 | Generated drafts, provider metadata, inline editing, and safety flags | yes | yes | yes | yes | implemented | `./scripts/verify-us-009.sh`; `POST /content/generate` + `frontend/e2e/content-generation.spec.ts` |
| US-010 | Content approval states, reviewer decisions, and review history | yes | yes | yes | yes | implemented | `./scripts/verify-us-010.sh`; approve/reject API + `frontend/e2e/content-approval.spec.ts` |
| US-011 | Approved-content copy/export, used-state updates, and handoff audit trail | yes | yes | yes | yes | implemented | `./scripts/verify-us-011.sh`; handoff API + `frontend/e2e/content-handoff.spec.ts` |
| US-012 | Lead creation, default pipeline states, duplicate guardrails, and baseline activity history | yes | yes | yes | yes | implemented | `./scripts/verify-us-012.sh`; lead API + `frontend/e2e/lead-pipeline.spec.ts` |
| US-013 | Lead-linked follow-up reminders, due/overdue queue, and baseline in-app reminder visibility | yes | yes | yes | yes | implemented | `./scripts/verify-us-013.sh`; reminders API + `frontend/e2e/follow-up-reminders.spec.ts` |
| US-014 | Dashboard overview cards, widget freshness, and explicit empty or unavailable metric states | yes | yes | yes | yes | planned |  |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.
