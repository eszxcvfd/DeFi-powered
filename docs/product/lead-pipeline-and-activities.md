# Lead Pipeline And Activities

Source: `SPEC.md` sections 4.4, 5.11, 5.12, `UI-006`, `UC-05`, and `AC-BIZ-08`.

## Product Goal

Sales and analyst users need the first internal lead workspace that turns
qualified events into trackable follow-up records. The product contract must
define how LiveLead creates leads from event context or manual entry, preserves
core qualification fields, applies duplicate guardrails, tracks pipeline-state
changes, and records enough activity history for later reminders and reporting.

## MVP Scope

This product slice covers:

- Creating leads from an event, organizer, speaker, or manual entry.
- Capturing the first lead fields needed for pipeline work: display name,
  company, title, public URL, discovery source, related event, interests, pain
  points, owner, status, lawful-basis note when needed, follow-up date, and
  notes.
- Applying the default pipeline states from newly discovered through not-fit or
  opportunity.
- Updating lead state and core notes from a lead-detail or pipeline surface.
- Showing leads in table and Kanban views with basic owner, campaign, source,
  and due-date filtering.
- Recording baseline activity history for lead creation, status changes, and
  manual notes.
- Duplicate guardrails that warn or block obvious duplicate leads before a
  second record is created.

This product slice does not yet cover:

- Reminder inboxes or overdue follow-up workflows.
- CSV import/export. The first bounded slice is defined in
  `docs/product/lead-import-export.md`.
- CRM synchronization.
- Dashboard or funnel reporting. Those read-model behaviors are defined in
  `docs/product/dashboard-overview-and-freshness.md` and
  `docs/product/funnel-reporting-and-conversion-steps.md` rather than this lead
  baseline.
- Full merge-resolution workflow for complex duplicates.
- Automatic outreach, browser-assisted sending, or outcome automation. Manual
  outcome tracking is defined in
  `docs/product/lead-outcomes-and-conversion-tracking.md` rather than this lead
  baseline.

## Contract Rules

- A lead must preserve either a source reference or an explicit manual-entry
  note so later review can explain where it came from.
- Lead creation must not rely on sensitive inferred traits or unsupported
  targeting signals.
- Duplicate checks must run before create using the stable identifiers
  available for the candidate record, such as public URL, external ID, email
  hash when present, or display-name plus company heuristics.
- Creating or updating a lead must preserve the related event or discovery
  source when that context exists.
- Pipeline-state changes and manual notes must append activity history with
  actor and timestamp rather than silently overwriting the story of the lead.
- Table and Kanban views must reflect the same underlying lead state even if
  they render different groupings.
- Follow-up date may be set in this slice, but reminder delivery and reminder
  queues are defined in `docs/product/follow-up-reminders-and-notifications.md`
  rather than this baseline story.
## API Surface

- `GET /leads`: list leads with filters and view-friendly summaries.
- `POST /leads`: create a lead from event-linked or manual context after
  duplicate checks.
- `GET /leads/{id}`: return lead detail, current pipeline state, and recent
  activity entries.
- `PATCH /leads/{id}`: update editable fields such as owner, notes, follow-up
  date, and pipeline state.
- Event-detail payloads or equivalent UI queries should expose whether a linked
  lead already exists so users do not create blind duplicates.

## UI Surface

The MVP lead slice should introduce `UI-006` without pulling in reporting:

- Lead table view.
- Lead Kanban view grouped by pipeline state.
- Create-lead entry from event-linked context and manual entry path.
- Quick note or equivalent lightweight activity entry.
- Filters for owner, campaign, source, and due date.

## Validation Implications

- Unit proof should cover duplicate matching, required-source or manual-entry
  rules, stage-transition guards, and activity-entry creation.
- Integration proof should cover lead create/update persistence, event-link
  preservation, and list or Kanban query behavior.
- E2E proof should cover creating a lead from an event, moving it across at
  least one stage, and confirming activity history is visible.
- Logs or audit proof should confirm who created, edited, or re-staged a lead.
- Platform proof should keep the future lead verification command wired into
  the Harness matrix before reminders or reporting stories build on it.
