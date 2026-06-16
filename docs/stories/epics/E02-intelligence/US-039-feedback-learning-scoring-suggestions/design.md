# Design

## Domain Model

The story should formalize the first governed scoring-suggestion objects:

- `ScoringSuggestionSet`: campaign-scoped review artifact generated from current
  feedback signals and active scoring context.
- `ScoringWeightDelta`: structured proposed change for one scoring component with
  current weight, proposed weight, delta, and rationale.
- `ScoringSuggestionSignal`: normalized supporting signal summary such as
  audience-feedback disagreement, hypothesis uncertainty, or other approved
  ranking-relevant evidence.
- `ScoringSuggestionDecision`: approval or rejection record with actor,
  timestamps, and optional review note.

Business rules:

- Suggestion generation must not directly mutate active campaign weights.
- Suggestions remain campaign-scoped and version-aware because the same signal
  pattern can imply different actions for different ICP strategies.
- Sparse or contradictory signals should lead to low confidence, a smaller
  suggestion set, or no suggestion at all.
- Applying an approved suggestion creates a new governed campaign weight
  snapshot instead of overwriting prior history invisibly.
- Rejected suggestions remain historical evidence and may inform later reviewed
  generations, but they must not alter active weights.

## Application Flow

- `GenerateScoringSuggestions` gathers current campaign weights, approved
  feedback signals, and ranking-relevant summaries, then produces a bounded
  suggestion set with structured deltas and confidence.
- `ValidateSuggestionSet` enforces supported scoring components, safe delta
  ranges, required rationale fields, and no-auto-apply behavior.
- `ApproveScoringSuggestionSet` checks authorization, writes a new campaign
  scoring-weight snapshot, marks the suggestion as approved, and records audit
  linkage between old and new profiles.
- `RejectScoringSuggestionSet` records a rejection decision with optional review
  note and keeps active weights unchanged.
- `ListScoringSuggestionHistory` returns recent campaign-scoped suggestion sets
  for review and comparison.

## Interface Contract

This baseline should add explicit suggestion-review endpoints rather than
editing campaign weights through opaque AI side effects:

- `POST /campaigns/{id}/scoring-suggestions:generate` creates a new suggestion
  set.
- `GET /campaigns/{id}/scoring-suggestions` returns recent suggestion sets and
  status.
- `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:approve` applies the
  proposed weight profile.
- `POST /campaigns/{id}/scoring-suggestions/{suggestion_id}:reject` records a
  rejection and optional note.

Expected payload concerns:

- Suggestion sets should include supporting signal summaries, proposed deltas,
  confidence, assumptions, and caution notes.
- Validation should reject unsupported components, unsafe deltas, stale
  campaign-scope mismatches, or approval attempts from unauthorized actors.
- Responses should make it explicit whether active campaign weights changed.

## Data Model

- Add durable storage for suggestion sets, component deltas, signal summaries,
  decision state, and actor timestamps.
- Reuse or extend campaign scoring-weight snapshot storage so approved
  suggestions create a new auditable version.
- Preserve enough linkage to AI feedback artifacts for evidence review without
  copying raw provider secrets or uncontrolled prompt data.
- Avoid introducing global learning tables or model-training infrastructure in
  this baseline.

## UI / Platform Impact

- Campaign scoring settings should gain a reviewable suggestion panel.
- Users should see current and proposed weights side by side, plus confidence
  and evidence cues.
- Approval and rejection controls must be restricted to authorized roles and
  provide clear result feedback.
- Platform work stays inside existing campaign, scoring, feedback, and audit
  boundaries; this is not a generalized optimization engine.

## Observability

- Record suggestion generations with campaign id, signal counts, confidence, and
  resulting proposed deltas.
- Record approval or rejection actions with actor, prior weight snapshot, and
  new snapshot linkage when applied.
- Keep diagnostics explainable enough that reviewers can understand why a
  suggestion existed without exposing secrets or hidden provider internals.

## Alternatives Considered

1. Auto-apply small deltas immediately. Rejected because `SPEC.md` requires
   reviewed feedback-learning rather than silent weight mutation.
2. Let users edit weights manually with no suggestion artifact. Rejected because
   the product needs a durable, explainable bridge from feedback to proposed
   ranking changes.
3. Build a global learning model across every tenant first. Rejected because the
   MVP contract is campaign-scoped and human-controlled.
