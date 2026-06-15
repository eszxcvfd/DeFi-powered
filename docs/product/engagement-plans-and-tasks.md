# Engagement Plans And Tasks

Source: `SPEC.md` sections 5.8, 5.9, 7.2, 12, `UI-004`, `UC-02`, and `UC-03`.

## Product Goal

Sales and analyst users need ranked events and audience insight to turn into a
concrete engagement plan before any AI-generated copy is produced. The product
contract must define how LiveLead creates a three-phase engagement plan,
structures tasks for before, during, and after the event, tracks task status
and ownership, preserves expected result / execution basis / estimated duration,
and applies value-first and anti-spam guardrails before the later
content-studio workflow arrives.

## MVP Scope

This product slice covers:

- Creating an engagement plan for a scored event within campaign context.
- Structuring tasks into `PRE_EVENT`, `LIVE_EVENT`, and `POST_EVENT` phases.
- Generating recommendations that differ depending on whether the event is
  currently `UPCOMING`, `LIVE`, or `ENDED`.
- Tracking task status, assignee, deadline, and notes for plan execution.
- Capturing channel, expected result, execution basis, and estimated duration
  for each suggested task.
- Showing an event-detail engagement view with plan phases and tasks.
- Carrying enough context from event review, score, and audience hypotheses to
  make the plan actionable.
- Preserving intermediary-first framing when the operator is opening an
  opportunity for a partner company rather than directly delivering the end
  service.
- Applying guardrails that keep plans relevant, value-first, and safe for later
  content generation.

This product slice does not yet cover:

- Generating AI content variants, prompts, or final copy.
- Reviewer approval workflow for generated content.
- Copy/export surfaces or “used” lifecycle for content.
- Automatic posting, bulk messaging, or browser-assisted execution.
- Lead creation or pipeline-stage changes.

## Contract Rules

- Every engagement plan must be linked to a canonical event and campaign scope.
- Plans must separate before, during, and after event tasks instead of storing
  a flat undifferentiated checklist.
- Plans must expose which event state and channel a suggestion is intended for.
- Tasks must support at least `TODO`, `IN_PROGRESS`, `DONE`, and `SKIPPED`,
  with assignee and deadline fields available when the workflow needs them.
- Every suggested task must keep `expected_result`, `execution_basis`, and
  `estimated_duration` as first-class data, not free-form comments only.
- Plan guidance must remain value-first and must not suggest spammy, deceptive,
  or unsupported claims about the event or audience.
- Plan guidance must support intermediary positioning such as introductions,
  opportunity opening, or partner framing when configured by the campaign.
- Engagement plans may reuse score and audience context, but they must not
  blur into generated content artifacts or approval state as if copy already
  exists.
- The MVP plan slice may use deterministic templates or rule-based suggestions
  first, but it must preserve enough structure for later AI content generation
  to reference the plan safely.
- Plan records and task changes must remain auditable enough for later review,
  especially when a task is skipped, revised, or reassigned.

## API Surface

- `POST /events/{id}/engagement-plans`: create or refresh an engagement plan
  for an event using current event, score, and audience context.
- `GET /events/{id}`: return current engagement plan summary and tasks needed
  for event-detail review.
- Plan and task payloads must expose phase, event state, channel, title,
  rationale, expected result, execution basis, estimated duration, status,
  assignee, deadline, and relevant context markers without implying content has
  been approved or sent.

## UI Surface

The MVP engagement slice should extend `UI-004` without claiming `UI-005`
content-studio behavior yet:

- Event detail engagement tab or equivalent section.
- Task groups for before, during, and after event phases.
- Playbook cards or equivalent summaries showing expected result, execution
  basis, and estimated time.
- Clear task status, assignee, and due-date cues.
- Empty-state or not-yet-generated messaging when a plan does not exist.

## Validation Implications

- Unit proof should cover plan-phase rules, task-state transitions, and
  guardrails that block spammy or unsupported plan suggestions.
- Integration proof should cover plan persistence, task updates, and event-detail
  API behavior.
- E2E proof should cover opening an event, generating or viewing a plan, and
  updating at least one task state.
- Logs or audit proof should confirm plan creation and task-state changes remain
  diagnosable without implying content approval or external action.
- Platform proof should keep engagement-plan verification wired into the
  Harness matrix for later content-studio and lead stories.
