# 0017 Scoring Suggestion Feedback Learning Baseline

Date: 2026-06-16

## Status

Accepted

## Context

`US-038` added governed AI feedback on discovery copilot responses and audience
hypotheses without mutating ranking behavior. `SPEC.md` and
`docs/product/feedback-learning-and-scoring-suggestions.md` require a
review-first bridge from those signals to campaign scoring-weight adjustments.
`US-039` must not auto-apply weights, must stay campaign-scoped, and must
preserve auditable history when weights change.

The slice touches authorization (scoring editors), audit actions, durable
suggestion and snapshot tables, campaign PATCH semantics for weights, and
campaign detail UI for side-by-side review.

## Decision

`US-039` introduces the first governed scoring-suggestion workflow:

- **`scoring_suggestion_sets`** stores campaign-scoped suggestion artifacts
  with status (`pending_review`, `approved`, `rejected`), structured signals,
  proposed deltas, current/proposed weight maps, and decision metadata.
- **`campaign_scoring_weight_snapshots`** records a new weight version when a
  suggestion is approved (`source=scoring_suggestion_approved`), linked to the
  suggestion set id.
- Generation uses deterministic heuristics over campaign-scoped feedback rollups
  (audience incorrect/uncertain with reason codes; copilot helpfulness). Safe
  per-component delta cap is **0.05**; generation never writes active campaign
  weights.
- REST contract:
  - `POST /campaigns/{id}/scoring-suggestions:generate`
  - `GET /campaigns/{id}/scoring-suggestions`
  - `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:approve`
  - `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:reject`
- Approval requires `require_scoring_editor` (analyst, admin, owner). Audit
  actions: `scoring_suggestion.generated`, `.approved`, `.rejected`.
- UI: campaign scoring weights panel exposes advisory messaging, generate,
  current-vs-proposed deltas, approve, and reject.

Out of scope for this baseline: cross-tenant learning, autonomous optimization,
prompt/model mutation from feedback, and full historical event simulation.

## Consequences

- Campaign weight changes from feedback always pass through an explicit approval
  step and leave snapshot + audit evidence.
- Multiple suggestion sets per campaign are allowed; only `pending_review` sets
  accept approve/reject.
- Later adaptive-ranking or AI-memory stories should extend signal sources or
  synthesis without bypassing this review gate.

## Proof

- `./scripts/verify-us-039.sh`
- `tests/unit/test_scoring_suggestions.py`
- `tests/integration/test_scoring_suggestions_api.py`
- `frontend/e2e/scoring-suggestion.spec.ts`