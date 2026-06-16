# AI Feedback And Learning Signals

Source: `SPEC.md` sections 4.2, 5.7, 5.8, 9.2, 9.3, and `UI-004`.

## Product Goal

Analysts and sales users need a lightweight way to mark whether AI-assisted
analysis was useful, incorrect, or uncertain so LiveLead can preserve
reviewable human feedback without silently changing ranking, prompts, or
automation behavior. The product contract should define the first governed
feedback slice for discovery copilot responses and audience hypotheses, with
structured reasons, actor attribution, and future-safe learning signals.

## MVP Scope

This product slice covers:

- Capturing per-user feedback on discovery-copilot responses with a positive or
  negative signal plus optional rationale.
- Capturing per-user feedback on audience hypotheses with `correct`,
  `incorrect`, or `uncertain` states plus optional rationale.
- Preserving reason codes and optional free-text notes that explain why a user
  agreed, disagreed, or lacked confidence.
- Showing the latest effective feedback state in discovery-copilot and
  audience-review surfaces.
- Storing enough tenant-scoped feedback metadata to support later scoring,
  prompt, or quality-review suggestions without auto-applying them.

This product slice does not yet cover:

- Automatic changes to scoring weights, prompt templates, models, or source
  selection from feedback alone.
- Multi-turn autonomous memory or generalized assistant personalization.
- Replacing content approval, rejection, or audit workflows already used for
  generated drafts.
- Workspace-wide analytics dashboards or feedback-driven experimentation
  controls.
- Feedback on browser-assisted external actions.

## Contract Rules

- Feedback is advisory and reviewable. It must never silently mutate the
  original discovery-copilot response, audience hypothesis, canonical event, or
  scoring record.
- Feedback must remain tenant-scoped and actor-attributed. Users may only view
  or modify feedback inside their own organization scope.
- The first slice should support one effective feedback state per user per
  target while preserving append-only history for audit and future analysis.
- Negative or uncertain feedback must support a structured reason code so later
  reviewers can distinguish low evidence, wrong audience fit, weak usefulness,
  or other failure modes.
- Free-text rationale is optional and must stay secret-safe, policy-safe, and
  bounded so it cannot become an uncontrolled prompt-injection channel.
- Feedback collection must not imply auto-learning. Any later suggestion to
  adjust scoring or prompt behavior remains a separate reviewed workflow.
- The product should keep discovery-copilot feedback and audience-feedback
  semantics distinct rather than flattening them into a single opaque thumbs
  counter.

## API Surface

- `PUT /discovery-copilot-responses/{id}/feedback`: create or update the
  current user's feedback for one copilot response.
- `PUT /audience-hypotheses/{id}/feedback`: create or update the current user's
  feedback for one audience hypothesis.
- Parent read surfaces such as `GET /events/{id}` and bounded discovery-copilot
  history responses may include the current user's feedback and lightweight
  aggregate counts when needed for review UX.
- Feedback payloads must expose target id, target type, effective state, reason
  code, optional note, actor, and timestamps without exposing provider secrets
  or internal prompt text beyond already allowed product context.

## UI Surface

- Discovery-copilot responses should expose lightweight thumbs or equivalent
  helpfulness controls with a reason capture step for negative feedback.
- Audience-hypothesis rows or cards should expose `correct`, `incorrect`, or
  `uncertain` actions with visible current-state feedback.
- Users should be able to revise their own feedback without editing the
  underlying AI output artifact.
- The first UX should make it obvious that feedback informs later review and
  suggestion workflows, not immediate autonomous model behavior.

## Validation Implications

- Unit proof should cover feedback-state validation, reason-code rules, update
  semantics, and no-auto-learning guardrails.
- Integration proof should cover tenant scoping, append-only history plus
  current-state projection, and API behavior for both target types.
- E2E proof should cover leaving feedback from discovery-copilot and event
  detail audience surfaces, then seeing the effective state reflected on
  refresh.
- Audit and log proof should confirm who changed feedback, for which target, and
  with which reason code without leaking secrets or raw provider internals.
- Platform proof should keep feedback verification wired into the Harness matrix
  before later scoring-adjustment or AI-memory stories widen scope.
