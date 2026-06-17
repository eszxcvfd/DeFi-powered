# Exec Plan

## Goal

Define a high-risk but bounded story that turns `FR-LEAD-007` into the first
governed lead CSV import/export contract for LiveLead without reopening CRM
sync, merge-resolution, or autonomous workflow scope.

## Scope

In scope:

- CSV export for the current lead filter set.
- CSV import preview with field mapping.
- Create-only apply semantics for preview rows marked ready.
- Duplicate classification that reuses `US-012`.
- Audit-safe import and export evidence.

Out of scope:

- CRM synchronization or webhook-driven ingest.
- XLSX or provider-specific import formats.
- Update-existing, merge, or overwrite semantics.
- Scheduled export delivery or artifact-history management.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.

Hard gates:

- The slice handles lead data and tenant-scoped imports.
- The slice adds new write paths that could create duplicates or weak
  provenance if the contract is underspecified.

## Work Phases

1. Discovery.
   Confirm the remaining `FR-LEAD-007` gap, review `US-012` duplicate and
   activity semantics, and align the story with the current lead contract.
2. Design.
   Define preview/apply boundaries, import-row classification semantics, role
   gates, and export safety rules.
3. Validation planning.
   Define proof for parsing, duplicate handling, audit safety, formula escaping,
   and tenant isolation.
4. Implementation.
   Future implementation should add tables, routes, UI states, and verify
   wiring without widening into CRM sync or merge resolution.
5. Verification.
   Future proof should use deterministic CSV fixtures that include ready,
   duplicate, invalid, and formula-prefixed rows.
6. Harness update.
   Keep the product doc, story packet, Harness story row, and trace evidence in
   sync.

## Stop Conditions

Pause for human confirmation if:

- The team wants update-existing or merge semantics in the same slice.
- Data-retention rules for import preview rows need a new organization-level
  policy surface rather than reuse of existing lead governance.
- Validation requirements need to weaken around duplicate safety or audit
  evidence.
- The product direction shifts from CSV portability into CRM sync or external
  ingestion.
