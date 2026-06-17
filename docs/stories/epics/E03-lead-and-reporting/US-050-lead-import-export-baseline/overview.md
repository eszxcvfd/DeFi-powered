# Overview

## Current Behavior

`US-012` gives LiveLead a first lead workspace with event-linked or manual
creation, duplicate guardrails, activity history, and table/Kanban views.
`US-019` gives reporting export for aggregated report surfaces, but the product
still has no governed way to import leads from a CSV or export the current lead
list itself. Teams that already maintain prospect lists outside LiveLead must
re-enter rows manually, and operators who want a CSV of the current filtered
lead set have to copy data by hand.

The current product docs explicitly leave this gap open:

- `docs/product/lead-pipeline-and-activities.md` excludes CSV import/export
  from the lead baseline.
- `SPEC.md` `FR-LEAD-007` requires CSV import/export with field mapping and
  preview before import.
- `FR-LEAD-004`, `FR-LEAD-005`, and `FR-ADM-001` mean the first import/export
  slice cannot bypass duplicate checks, activity history, or audit evidence.

## Target Behavior

This story should establish the first bounded lead CSV import/export slice:

- Users can export the current lead table to CSV using the same tenant and
  filter rules as the lead list.
- Users can upload a CSV, map columns to bounded lead fields, and preview the
  file before any write occurs.
- Preview classifies each row as ready, duplicate, or invalid using the
  existing duplicate rules from `US-012`.
- Apply is create-only: ready rows are created as leads, duplicate or invalid
  rows are skipped, and the result is summarized with durable audit evidence.
- Imported leads preserve provenance through mapped source fields or a required
  job-level provenance note.
- Exported CSV remains safe to open in spreadsheets by escaping
  formula-injection prefixes.

## Affected Users

- Sales/BD users who bulk-load prospect lists into the lead pipeline.
- Analysts who curate and hand off lead sets for follow-up.
- Owners/Admins who need import/export auditability and tenant-safe boundaries.

## Affected Product Docs

- `docs/product/lead-pipeline-and-activities.md`
- `docs/product/lead-import-export.md`

## Non-Goals

- CRM synchronization or bidirectional external sync.
- XLSX, Sheets, or provider-specific import formats.
- Auto-merge, overwrite, or update-existing behavior during import.
- Scheduled export delivery, webhook fan-out, or artifact hosting.
- Bulk enrichment, dedupe-resolution workflow, or autonomous outreach.
