# Design

## Domain Model

The story should formalize the first lead-workflow objects:

- `LeadRecord`: canonical lead entity with origin, qualification fields, owner,
  follow-up date, and pipeline state.
- `LeadOrigin`: value object describing event-linked or manual-entry source
  context.
- `LeadStage`: ordered pipeline state set covering newly discovered through not
  fit or opportunity.
- `LeadActivityEntry`: append-only history item for creation, manual notes, and
  state changes.
- `LeadDuplicateMatch`: duplicate-check result that can block or warn before
  create.

Business rules:

- A lead must keep either source provenance or an explicit manual-entry note.
- Duplicate checks must run before create against the stable identity signals
  available for that candidate lead.
- Creating a lead from inferred sensitive traits is not allowed.
- State changes and manual notes must append activity history rather than
  rewrite prior context.

## Application Flow

- `CreateLeadFromEvent` and `CreateLeadManual` commands validate origin,
  duplicate signals, and default stage assignment.
- `UpdateLeadDetails` handles owner, notes, follow-up date, and editable
  qualification fields.
- `TransitionLeadStage` records pipeline movement as both state change and
  activity event.
- `ListLeads` and `GetLeadDetail` queries serve table, Kanban, and detail
  views.
- Event detail or equivalent context query should surface linked-lead summary
  data to avoid blind duplicate creation.

## Interface Contract

Backend contract should minimally support:

- `GET /leads`
- `POST /leads`
- `GET /leads/{id}`
- `PATCH /leads/{id}`

Expected payload concerns:

- Create requests accept event-linked or manual-entry lead context.
- Responses expose current stage, owner, follow-up date, duplicate-check
  outcome when relevant, and recent activity entries.
- Validation errors should distinguish missing-origin problems, unsupported
  sensitive-data usage, and duplicate conflicts.

## Data Model

- Add durable lead storage for core fields, origin references, current stage,
  and follow-up date.
- Add append-only lead-activity storage linked to lead id and actor metadata.
- Store duplicate-check fingerprints or queryable identity fields needed for
  pre-create matching and later reconciliation.
- Preserve compatibility with later reminders, reporting, import/export, and
  merge workflows without forcing those tables into this first slice.

## UI / Platform Impact

- Add a lead pipeline surface that can render both table and Kanban views from
  one underlying lead query.
- Add event-linked create-lead affordance or lead summary inside existing event
  review surfaces.
- Expose lightweight note entry and visible state-change feedback.
- Keep reporting widgets, reminder inboxes, and browser-assisted actions
  visibly deferred.

## Observability

- Record audit-friendly events for lead creation, duplicate-block decisions,
  manual note creation, and stage changes.
- Keep enough structured fields in logs to relate a lead update back to event
  and source provenance when present.

## Alternatives Considered

1. Start E03 with reporting widgets before durable lead records exist. Rejected
   because dashboard metrics would have no trustworthy pipeline source of truth.
2. Skip activity history in the first slice and rely only on current lead
   fields. Rejected because later reminders and outcomes need an explainable
   lead timeline.
3. Include full duplicate merge workflow immediately. Rejected because the
   first slice only needs baseline guardrails, not multi-record reconciliation.
