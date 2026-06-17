# Validation

## Proof Strategy

This story is done when LiveLead can preview a CSV import, explain which rows
will be created or skipped, apply only ready rows, and export the current lead
table to CSV without weakening tenant isolation, duplicate guardrails, or audit
evidence.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | CSV parsing, delimiter/header validation, field mapping rules, required-field checks, duplicate classification reuse from `US-012`, create-only apply behavior, and spreadsheet-formula escaping on export. |
| Integration | Preview-job persistence, row classification persistence, tenant-scoped row lookup, apply summary counts, lead activity creation for imported rows, and filtered CSV export shape. |
| E2E | Authenticated analyst or sales user uploads a mixed CSV, maps columns, reviews ready/duplicate/invalid rows, applies the import, confirms created leads appear in table/Kanban, then exports the filtered list to CSV. |
| Platform | `scripts/verify-us-050.sh` exercises migrations, backend tests, frontend flow, and the Harness story verification command. |
| Performance | Preview and apply remain bounded for a representative CSV size; export does not time out on a normal filtered lead set. |
| Logs/Audit | Preview, apply, and export write secret-safe audit entries with actor, organization, counts, and filter/mapping summaries without raw CSV payload leakage. |

## Fixtures

- One organization with owner, analyst, sales, reviewer, and viewer users.
- Existing leads that exercise duplicate detection by public URL and by display
  name plus company.
- A deterministic CSV fixture with:
  - one ready row
  - one duplicate row
  - one invalid row missing required fields
  - one row with a formula-prefixed cell that must be escaped on export
- Optional campaign context fixture for import preview.

## Commands

Add commands after scripts exist.

```text
TBD
```

## Acceptance Evidence

Add results after verification.
