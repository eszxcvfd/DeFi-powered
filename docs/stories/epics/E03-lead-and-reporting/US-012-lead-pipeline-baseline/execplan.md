# Exec Plan

## Goal

Define and implement the minimum lead-pipeline slice that lets LiveLead create
trackable leads from qualified event context, move them through default stages,
and keep baseline activity and duplicate-guardrail behavior before reminders or
reporting are added.

## Scope

In scope:

- Lead creation from event-linked or manual-entry context.
- Core lead fields and default pipeline states.
- Table and Kanban-compatible lead retrieval.
- Baseline activity history for create, note, and state changes.
- Duplicate guardrails before create.

Out of scope:

- Reminder inboxes or overdue workflows.
- CSV import/export or CRM sync.
- Reporting dashboards or funnel metrics.
- Full duplicate merge or archive workflows.
- Automated outreach or browser-assisted send flows.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None triggered directly, but the lane stays high-risk because this story adds
  new durable records, user-visible workflow, and cross-domain event-to-lead
  behavior.

## Work Phases

1. Discovery: confirm lead creation, stage, duplicate, and activity rules from
   `SPEC.md`, `UC-05`, and `UI-006`.
2. Design: define lead entities, API surface, duplicate guardrails, and
   activity-history boundaries without dragging in reporting or reminders.
3. Validation planning: design proof for create/update flows, stage changes,
   duplicate conflicts, and event-linked lead visibility.
4. Implementation: add lead persistence, list/detail contracts, pipeline UI,
   and baseline history behavior.
5. Verification: prove create, update, pipeline movement, and duplicate
   guardrails end to end.
6. Harness update: record the new E03 contract and leave a clean handoff for
   reminder, reporting, and import/export stories.

## Stop Conditions

Pause for human confirmation if:

- Duplicate handling needs merge or archival semantics beyond warn-or-block.
- Lead creation needs private or sensitive contact enrichment beyond public
  source data.
- Reminder ownership or reporting requirements are pulled into this story.
- Validation requirements need to be weakened because the UI surface becomes
  too large for one slice.
