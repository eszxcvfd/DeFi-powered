# Feedback Learning And Scoring Suggestions

Source: `SPEC.md` sections 5.7, 5.8, 9.2, 9.3, and `UI-004`.

## Product Goal

Owners, admins, and analysts need a governed way to review whether accumulated
feedback suggests the current campaign scoring weights are overvaluing or
undervaluing certain factors. The product contract should define a review-first
feedback-learning slice that turns validated feedback signals into explainable
weight-adjustment suggestions without auto-changing ranking behavior.

## MVP Scope

This product slice covers:

- Aggregating approved feedback signals that are relevant to event prioritization
  inside one campaign scope.
- Generating a bounded set of suggested scoring-weight adjustments with reasons,
  evidence summary, and confidence.
- Showing the current weight profile beside the proposed weight profile and
  projected directional impact.
- Requiring explicit human review and approval before any suggestion changes the
  campaign's active scoring weights.
- Preserving suggestion history, approval state, and provenance for audit and
  later comparison.

This product slice does not yet cover:

- Automatic live re-optimization of scoring weights.
- Black-box model retraining from raw feedback.
- Cross-tenant or global learning shared across organizations.
- Real-time simulation across every historical event result.
- Generalized AI-memory or prompt-personalization behavior.

## Contract Rules

- Feedback-derived suggestions are advisory. They must never change active
  scoring weights until an authorized user approves them.
- Suggestions must remain campaign-scoped because each campaign can target a
  different market, ICP, and weighting strategy.
- The product must distinguish between source signals such as audience-feedback
  correctness, discovery-copilot usefulness, and downstream ranking evidence
  instead of flattening them into one opaque score.
- Every suggestion must explain which signals contributed, which weight
  components are proposed to change, and why the system believes the change may
  improve prioritization.
- Suggestions must include uncertainty or low-signal messaging when feedback is
  too sparse, contradictory, or stale.
- The system may use deterministic heuristics, model-assisted synthesis, or
  both, but the output must stay structured, reviewable, and secret-safe.
- Approval of a suggestion updates campaign scoring settings through a governed
  workflow and must create a new auditable weight snapshot rather than mutating
  prior history invisibly.

## API Surface

- `POST /campaigns/{id}/scoring-suggestions:generate`: create a bounded reviewable
  suggestion set from current feedback signals and campaign scoring context.
- `GET /campaigns/{id}/scoring-suggestions`: list recent suggestion sets with
  status, summary, and timestamps.
- `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:approve`: apply an
  approved suggestion to campaign scoring weights and create a new weight
  snapshot.
- `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:reject`: record a
  rejection reason without changing active weights.

## UI Surface

- Campaign scoring settings should expose a bounded review panel for
  feedback-derived suggestions.
- Each suggestion set should show current versus proposed weights, evidence
  summary, confidence, and risk or caution notes.
- Authorized users should be able to approve or reject a suggestion set with
  clear state feedback.
- The first UX should make it obvious that suggestions are optional and do not
  rewrite historical decisions automatically.

## Validation Implications

- Unit proof should cover signal-threshold rules, suggestion-shape validation,
  approval gating, and no-auto-apply guardrails.
- Integration proof should cover campaign scoping, suggestion persistence,
  approval or rejection flows, and new weight-snapshot creation.
- E2E proof should cover generating a scoring suggestion, reviewing the proposed
  changes, approving or rejecting it, and seeing campaign weights update only
  after approval.
- Audit and log proof should confirm who generated, approved, or rejected a
  suggestion and which weight deltas were involved.
- Platform proof should keep scoring-suggestion verification wired into the
  Harness matrix before broader AI-memory or adaptive-ranking stories widen
  scope.
