# Design

## Domain Model

The story should formalize the first governed AI-feedback objects:

- `AiFeedbackTarget`: typed target reference for one supported analysis artifact,
  initially `discovery_copilot_response` or `audience_hypothesis`.
- `AiFeedbackEntry`: actor-attributed feedback event with effective state,
  structured reason code, optional note, and timestamps.
- `AiFeedbackProjection`: current effective feedback view for one user/target,
  derived from append-only history.
- `AiFeedbackAggregate`: lightweight aggregate counts or state summaries used by
  review surfaces without implying automated learning.

Business rules:

- Feedback never mutates the underlying AI output artifact as if the output were
  regenerated.
- Discovery-copilot feedback and audience-hypothesis feedback share storage
  patterns but keep separate state vocabularies.
- One user may revise feedback for the same target, but history stays auditable.
- Negative or uncertain feedback must preserve a structured reason code.
- Feedback is advisory input for later reviewed workflows, not an autonomous
  training trigger.

## Application Flow

- `RecordDiscoveryCopilotFeedback` validates campaign scope, accepted state
  values, reason requirements, and optional note bounds before persisting a new
  history entry and updating the current projection.
- `RecordAudienceHypothesisFeedback` validates event scope plus the
  `correct`/`incorrect`/`uncertain` vocabulary before persisting feedback.
- `GetFeedbackProjectionForViewer` attaches the current viewer's feedback state
  to discovery-copilot and audience-review payloads.
- `SummarizeFeedbackSignals` may expose bounded aggregate counts for operators or
  later reviewed suggestion workflows without creating a generic analytics
  surface yet.
- `GuardAgainstAutoLearning` keeps feedback events from directly invoking prompt
  mutation, scoring-weight changes, or connector-selection changes.

## Interface Contract

This baseline should add target-scoped feedback APIs rather than a generic
unbounded AI memory endpoint:

- `PUT /discovery-copilot-responses/{id}/feedback` upserts the current user's
  effective feedback state for one copilot response.
- `PUT /audience-hypotheses/{id}/feedback` upserts the current user's effective
  feedback state for one audience hypothesis.
- Parent read routes may return `viewer_feedback` and bounded aggregate counts
  when needed for review UX.

Expected payload concerns:

- Discovery-copilot feedback accepts a positive/negative state plus reason code
  and optional note.
- Audience feedback accepts `correct`, `incorrect`, or `uncertain` plus reason
  code and optional note.
- Validation should reject unsupported target types, invalid state transitions,
  or out-of-scope cross-tenant targets.

## Data Model

- Add append-only feedback-event storage with target type, target id, actor id,
  effective state, reason code, optional note, and timestamps.
- Add a current-state projection or equivalent query pattern so UI surfaces can
  render the latest feedback efficiently.
- Preserve linkage to campaign/event context needed for audit and later reviewed
  quality work.
- Avoid introducing model-tuning, experimentation, or analytics tables in this
  baseline.

## UI / Platform Impact

- Discovery-copilot UI should show a lightweight helpful/not-helpful control
  with a reason capture step when needed.
- Event-detail audience UI should show `correct`, `incorrect`, or `uncertain`
  feedback controls near each hypothesis.
- Surfaces should reflect the current user's latest feedback clearly without
  implying that the underlying AI output was edited.
- Platform work stays within existing tenant, audit, and AI-provider boundaries;
  this is not yet a generalized memory subsystem.

## Observability

- Record audit-friendly feedback events with actor, target type/id, prior state,
  new state, and reason code.
- Preserve enough counters to support later quality dashboards or scoring-review
  suggestions without requiring those dashboards now.
- Keep notes and reason payloads secret-safe and bounded so feedback storage does
  not become an uncontrolled prompt source.

## Alternatives Considered

1. Reuse content approval or rejection states for all AI outputs. Rejected
   because discovery guidance and audience analysis need lightweight correctness
   feedback, not publication workflow states.
2. Store only free-text comments. Rejected because later quality workflows need
   structured signals that are comparable across targets.
3. Auto-adjust prompts or scoring weights immediately from feedback. Rejected
   because `SPEC.md` keeps learning changes review-gated.
