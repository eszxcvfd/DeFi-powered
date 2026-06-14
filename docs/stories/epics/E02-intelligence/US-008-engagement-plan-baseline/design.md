# Design

## Domain Model

The story should formalize the first engagement-planning objects:

- `EngagementPlan`: plan record linked to an event and campaign.
- `EngagementTask`: actionable task record within a plan.
- `EngagementPhase`: phase marker for `PRE_EVENT`, `LIVE_EVENT`, and
  `POST_EVENT`.
- `PlanGenerationContext`: metadata that captures which event, score, and
  audience inputs shaped the plan.

Business rules:

- A plan must belong to an event and campaign scope.
- Tasks must remain phase-specific rather than collapsing all work into one
  flat list.
- Task states must support at least `TODO`, `IN_PROGRESS`, `DONE`, and
  `SKIPPED`.
- Plans should stay value-first and must not encode spammy, deceptive, or
  unsupported claims as recommended actions.
- Plan generation may start deterministic or rules-based, but it must preserve
  enough structure for future content generation to reference tasks safely.
- Task updates must not imply that external posting, messaging, or approval has
  already happened.

## Application Flow

Commands:

- Create or refresh an engagement plan for a scored event.
- Persist tasks with phase, rationale, status, assignee, and deadline fields.
- Update task state or notes as the user works through the plan.

Queries:

- Get event detail with current engagement plan and grouped tasks.
- Detect whether an event has no plan, a stale plan, or an active plan.

Plan generation should live behind domain or application boundaries so the
first implementation can use deterministic task templates and later adopt AI
assistance without breaking the contract. Engagement planning should consume
event, score, and audience context without owning those source domains.

## Interface Contract

The minimum contract should cover:

- `POST /events/{id}/engagement-plans` to create or refresh a plan.
- `GET /events/{id}` with engagement-plan summary and grouped tasks.
- Stable payload fields for `phase`, `title`, `rationale`, `status`,
  `assignee`, `deadline`, and plan metadata.
- Clear empty or not-yet-generated states when a plan does not exist.

Errors should distinguish missing event scope, unavailable planning context,
invalid task updates, and missing plan records without exposing storage
internals.

## Data Model

Expected persistence work:

- Add engagement-plan storage linked to canonical events and campaigns.
- Add engagement-task storage for phase, title, rationale, status, assignee,
  deadline, and notes.
- Preserve creation and update timestamps for auditability.
- Avoid pulling generated-content, reviewer, or lead-pipeline tables into this
  story.

## UI / Platform Impact

- Extend event detail with an engagement tab or section aligned with `UI-004`.
- Show grouped tasks for before, during, and after event phases.
- Support updating at least basic task state in the UI.
- Keep content-studio, approval, and lead actions visibly deferred.

## Observability

- Record plan creation, refresh, and task-state changes in structured logs or
  audit-friendly traces.
- Keep it diagnosable why a task was suggested and when it changed state.
- Ensure logs do not imply content approval, external sending, or browser
  execution when those actions have not happened.

## Alternatives Considered

1. Jump straight to AI content generation without a separate plan artifact.
   Rejected because users need a phase-based execution scaffold before copy
   variants are meaningful.
2. Treat engagement planning as frontend-only state. Rejected because task
   ownership, auditability, and later content generation need a durable plan.
