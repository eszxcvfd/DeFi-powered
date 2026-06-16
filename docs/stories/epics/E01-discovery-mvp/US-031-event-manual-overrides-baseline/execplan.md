# Exec Plan

## Goal

Define and implement the first governed canonical-event edit workflow so
LiveLead can preserve manual corrections, retain event change history, and keep
source provenance trustworthy when normalized event data needs human repair.

## Scope

In scope:

- Authorized manual edits for a bounded set of canonical event fields.
- Append-only change history for event edits and clear-override actions.
- Clear-override behavior that restores source-backed canonical values.
- Overwrite protection against later automatic normalization.
- Event detail projection for override badges or field provenance summary.
- Audit-safe edit diagnostics.

Out of scope:

- Bulk event editing.
- Event merge, split, or delete governance.
- Direct source-observation editing.
- Approval workflow for event edits.
- Calendar export or external-system sync.

## Risk Classification

Risk flags:

- Authorization.
- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Authorization.
- Audit/security.
- Data migration or deletion risk appears.

## Work Phases

1. Discovery: confirm manual-override, provenance, and history requirements
   from `SPEC.md`, event review, and downstream event consumers.
2. Design: define override ownership, protected-field semantics, change
   history, and stale-read safeguards for dependent views.
3. Validation planning: design proof for authorized edits, overwrite
   protection, clear-override restoration, and event-history queries.
4. Implementation: add durable override storage or fields, event edit APIs, and
   event-detail UI for edits plus history.
5. Verification: prove edits, history, authorization, and override-protection
   behavior work without corrupting source evidence.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for bulk edit or sync stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The team wants merge, delete, or bulk-edit behavior folded into the baseline.
- Downstream score, reminder, or notification freshness rules cannot be made
  explicit without a broader product decision.
