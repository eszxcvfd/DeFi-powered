# Exec Plan

## Goal

Define and implement the first manual lead-outcome slice that records contact,
response, meeting, and opportunity facts in durable lead history, optionally
links them to used content, and prepares trustworthy data for later funnel and
content-effectiveness stories.

## Scope

In scope:

- Manual outcome recording on a lead.
- Outcome timeline history and latest-outcome summary.
- Optional outcome linkage to existing content records.
- Baseline validation for invalid or contradictory outcome recordings.

Out of scope:

- Funnel charts or aggregate reporting screens.
- CRM sync or webhook-driven outcome ingestion.
- Automatic outcome detection from browser or messaging systems.
- Revenue forecasting or advanced opportunity management.
- Full content-effectiveness comparison logic.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None directly, but the lane stays high-risk because this story introduces new
  durable conversion facts across lead, content, and later reporting surfaces.

## Work Phases

1. Discovery: confirm outcome, timeline, and reporting dependencies from
   `SPEC.md`, `FR-LEAD-005`, `FR-REP-001`, `FR-REP-002`, and the KPI question in
   section 17.
2. Design: define outcome types, optional content linkage, and contradiction
   rules without widening into funnel or CRM sync.
3. Validation planning: design proof for outcome recording, timeline rendering,
   invalid combinations, and linked-content behavior.
4. Implementation: add durable outcome persistence, lead-surface summaries, and
   the first manual outcome action.
5. Verification: prove users can record outcomes and see them appear as durable
   timeline facts.
6. Harness update: leave a clean handoff for funnel, content-effectiveness, and
   CRM-sync stories.

## Stop Conditions

Pause for human confirmation if:

- Outcome recording needs automatic external ingestion rather than manual MVP
  entry.
- Funnel visualization or content-effectiveness analytics starts to creep into
  the same slice.
- The product needs revenue-stage modeling beyond opportunity.
- Validation requirements need to weaken because outcome and lead-state rules are
  more complex than one baseline slice can cover safely.
