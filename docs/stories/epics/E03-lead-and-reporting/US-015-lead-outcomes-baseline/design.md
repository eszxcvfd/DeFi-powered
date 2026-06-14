# Design

## Domain Model

The story should formalize the first conversion-fact objects in the lead domain:

- `LeadOutcomeEntry`: append-only outcome record linked to one lead.
- `OutcomeType`: controlled set for the first reportable milestones: contact,
  response, meeting, and opportunity.
- `OutcomeContentLink`: optional reference from an outcome to content already
  used in the product.
- `LatestLeadOutcome`: read model for lead detail, list, or pipeline cues.

Business rules:

- Outcome entries must preserve actor, occurred-at time, notes, and lead id.
- Outcome history must remain append-only even when the lead's current stage
  later changes again.
- Outcome types should map cleanly to later funnel steps without forcing funnel
  reporting into this story.
- Content linkage is optional, but when present it must reference a durable
  content record that is already in an appropriate lifecycle state.
- The system should block obviously incompatible outcome recordings or surface
  them clearly rather than storing contradictory facts silently.

## Application Flow

- `RecordLeadOutcome` validates lead existence, outcome type, optional linked
  content, and contradiction guards before appending a timeline entry.
- Lead detail and list queries should include latest-outcome summary without
  requiring a separate reporting surface.
- Outcome history queries should support timeline rendering alongside notes,
  stage changes, and reminder actions.
- Dashboard and funnel stories should consume the durable outcome entries later
  rather than inventing separate conversion facts.

## Interface Contract

Backend contract should minimally support:

- Outcome-create action on a lead or equivalent endpoint.
- Lead payload latest-outcome summary fields.
- Timeline-ready outcome history entries with actor, type, occurred-at time,
  notes, and optional linked content context.

Expected payload concerns:

- Errors should distinguish missing lead, invalid outcome type, invalid content
  reference, and incompatible lead-state combinations.
- Outcome identifiers and type keys should stay stable enough for later reporting
  queries and export workflows.

## Data Model

- Extend durable lead activity storage or equivalent outcome storage so outcome
  entries remain first-class data rather than notes-only text.
- Preserve optional content linkage and outcome-type fields needed for later
  attribution and aggregation.
- Reuse existing lead timeline and audit structures where possible instead of
  creating disconnected conversion logs.
- Preserve compatibility with later funnel metrics, source-performance slicing,
  content-effectiveness analysis, and CRM-sync bridges.

## UI / Platform Impact

- Add a manual record-outcome action in the lead workspace.
- Show outcome entries within lead activity history.
- Show latest-outcome summary or badge in lead detail and pipeline views.
- Keep funnel charts, attribution comparisons, and CRM-sync controls visibly
  deferred.

## Observability

- Record audit-friendly events for outcome creation, invalid outcome attempts,
  and linked-content references when present.
- Keep enough structured fields to explain how an outcome entered reporting data
  without relying on ambiguous free-text notes.

## Alternatives Considered

1. Derive funnel and conversion truth only from current lead stage. Rejected
   because stage alone loses the explicit timeline fact and optional content
   linkage needed for explainable reporting.
2. Wait for CRM sync before recording any outcomes. Rejected because MVP still
   needs a manual path to prove lead-to-outcome workflow before external systems
   exist.
3. Store outcomes only as generic notes. Rejected because reporting and content
   attribution would become unreliable and hard to validate.
