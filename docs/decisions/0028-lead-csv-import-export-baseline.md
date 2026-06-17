# 0028 Lead CSV Import/Export Baseline

Date: 2026-06-17

## Status

Proposed (companion decision to `US-050`).

## Context

`SPEC.md` `FR-LEAD-007` requires CSV import/export with field
mapping and preview before import:

> **FR-LEAD-007 — Lead CSV import/export**
> **Ưu tiên:** Should
> Bulk import/export lead với field mapping và preview
> trước khi import.

`US-012` shipped the first lead workspace with event-linked or
manual creation, duplicate guardrails, activity history, and
table/Kanban views. `US-019` shipped aggregated report export
(CSV and printable). The product still has no governed way to
import leads from a CSV or export the current filtered lead
set itself.

The product docs explicitly leave this gap open:

- `docs/product/lead-pipeline-and-activities.md` excludes CSV
  import/export from the lead baseline.
- `docs/product/lead-import-export.md` defines the contract
  rules and the API surface for the first bounded slice.
- `FR-LEAD-004`, `FR-LEAD-005`, and `FR-ADM-001` mean the first
  import/export slice cannot bypass duplicate checks, activity
  history, or audit evidence.

## Decision

The first bounded slice for `US-050` is:

1. **CSV import preview**, with field mapping, a required
   job-level provenance note, and a row-by-row classification
   of `ready`, `duplicate`, or `invalid` *before* any write.
2. **Create-only apply**, applied only to rows classified as
   `ready`. Duplicate and invalid rows are surfaced during
   preview and skipped during apply; they are not merged,
   updated, or overwritten.
3. **Duplicate classification that reuses `US-012`**. The
   import surface calls the existing `find_duplicate` helper
   from `src/livelead/domain/leads/validation.py` so the
   preview cannot drift from the manual-create duplicate
   contract.
4. **Activity-history reuse**. Each imported lead records the
   same `LeadActivityKind.CREATED` entry used by manual
   creation, with body `Imported from CSV (job {id})`, so
   reminders, reporting, and audit reads treat imported leads
   exactly like manually created leads.
5. **Export** mirrors the existing `GET /leads` filter
   semantics. The CSV body escapes spreadsheet-formula
   prefixes (`=`, `+`, `-`, `@`, tab, carriage return) so
   downloads do not introduce formula-injection risk when
   opened in spreadsheet tools.
6. **Audit**. The slice emits `lead.import.previewed`,
   `lead.import.applied`, and `lead.export.downloaded` audit
   entries with secret-safe payloads (no raw row payload, no
   raw CSV body, mapping summary, count summary, and filter
   snapshot only).
7. **Role gate**. The first slice restricts import and export
   to roles that can edit the lead pipeline: `owner`, `admin`,
   and `sales_bd`. `viewer` and `reviewer` receive
   `LEAD_IMPORT_FORBIDDEN` and `LEAD_EXPORT_FORBIDDEN` errors
   with the same envelope as the rest of the lead surface.
8. **Persistence**. The slice persists only the file hash,
   filename, delimiter, mapping snapshot, provenance note,
   and normalized row payloads needed for preview and
   auditability. The raw CSV blob is not stored.
9. **Validation surface**. CSV parsing, mapping validation,
   duplicate classification, formula escaping, and
   create-only apply behavior are pure-domain helpers
   covered by unit tests; preview persistence, organization
   scoping, apply summary counts, activity creation, and
   export shape are covered by integration tests against the
   FastAPI surface; the deterministic CSV fixture is wired
   into `scripts/verify-us-050.sh`.

## Out of scope

- CRM synchronization, webhook-driven ingest, or
  bidirectional external sync.
- XLSX, Google Sheets, or arbitrary file-format support.
- Auto-merge or in-place update of existing leads during
  import.
- Bulk delete, bulk reassignment, or enrichment during
  import.
- Scheduled export delivery, report bundles, or external
  storage artifact management.
- Persisting the raw CSV blob for later replay.

## Consequences

- The first slice does not widen the lead domain model
  beyond the existing `LeadRecord`. New tables
  `lead_import_jobs` and `lead_import_rows` carry
  preview-only metadata and the activity-history contract
  continues to flow through `LeadActivityRow`.
- The `LeadImportExportService` is the only place that
  mutates the import tables and emits the new audit
  actions. The REST layer is a thin parser and role-gate
  wrapper.
- The export endpoint reuses the lead-list repository so
  filter semantics stay aligned with the lead table. No
  parallel filter system is introduced.
- The secret-safe payload contract from `US-041` and
  `US-026` is enforced before persistence in
  `AuditService.emit`. The mapping snapshot and the
  classification counts are always included; raw row
  payload and raw CSV body are always excluded.

## References

- `docs/product/lead-pipeline-and-activities.md`
- `docs/product/lead-import-export.md`
- `docs/stories/epics/E03-lead-and-reporting/US-050-lead-import-export-baseline/`
- `SPEC.md` `FR-LEAD-007`, `FR-LEAD-004`, `FR-LEAD-005`,
  `FR-ADM-001`
- `docs/ARCHITECTURE.md` (Parse-First Rule, Command/Query
  Separation, Tenant and Permission Enforcement)
