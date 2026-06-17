# Design

## Domain Model

The first slice adds a bounded import/export seam on top of the existing lead
domain without redefining lead semantics from `US-012`.

Primary entities and value objects:

- `LeadImportJob`: organization-scoped preview/apply record with actor,
  filename, file hash, delimiter, mapping snapshot, provenance note, optional
  campaign context, status, and summary counts.
- `LeadImportRow`: one normalized preview row owned by an import job with row
  number, mapped field payload, classification (`ready`, `duplicate`,
  `invalid`, `imported`, `skipped`), duplicate-match reference, and validation
  errors.
- `LeadExportRequest`: bounded query object that mirrors the lead-table filters
  already accepted by the lead list query.
- `LeadImportClassification`: value object that captures why a row is ready,
  duplicate, or invalid so the preview UI and audit log share the same
  semantics.

Business rules:

- Preview is mandatory before apply.
- Apply is create-only in the first slice.
- Duplicate classification must reuse the existing lead duplicate heuristics
  rather than introducing a second duplicate engine.
- Every created row appends the same activity-history semantics used by manual
  lead creation, with an activity reason such as `imported_from_csv`.
- Export may include only fields already visible or acceptable on the lead
  surface; no raw duplicate heuristics or hidden internals.
- Export must escape spreadsheet-formula prefixes.

## Application Flow

1. `PreviewLeadCsvImport` accepts the uploaded file, field mapping, provenance
   note, and optional campaign context.
2. The service parses the CSV, normalizes rows into bounded lead fields, runs
   per-row validation, and classifies duplicates against the current
   organization.
3. The preview persists a `LeadImportJob` plus `LeadImportRow` snapshots and
   returns counts plus the new job id.
4. `GetLeadImportJob` and `ListLeadImportRows` power the preview UI and allow
   users to inspect duplicate or invalid rows before apply.
5. `ApplyLeadCsvImport` loads the preview job, verifies it is still in
   previewable state, creates leads only for `ready` rows, appends lead
   activities, marks imported or skipped rows, and returns a durable summary.
6. `ExportLeadCsv` reuses the existing lead-list query path, serializes the
   current filtered results to CSV, escapes risky cell prefixes, and writes an
   audit entry for the download.

## Interface Contract

Routes:

- `POST /leads/imports:preview`
- `GET /leads/imports/{id}`
- `GET /leads/imports/{id}/rows?status=&limit=&offset=`
- `POST /leads/imports/{id}:apply`
- `GET /leads/export.csv?...`

Request/response expectations:

- Preview request includes multipart CSV file, `mapping` JSON, required
  `provenance_note`, and optional `campaign_id`.
- Preview response returns `import_job_id`, `status`, `ready_count`,
  `duplicate_count`, `invalid_count`, detected headers, and mapping snapshot.
- Row-list response returns normalized row payload, classification,
  duplicate-match summary, and error array.
- Apply response returns `created_count`, `skipped_duplicate_count`,
  `skipped_invalid_count`, `job_status`, and the created lead ids when the
  count is small enough to return inline.
- Export returns `text/csv` plus filename metadata; unauthorized users receive
  the same error envelope and tenant-safe denial behavior as the lead list.

Error contracts:

- `LEAD_IMPORT_FILE_INVALID`
- `LEAD_IMPORT_FILE_TOO_LARGE`
- `LEAD_IMPORT_MAPPING_INVALID`
- `LEAD_IMPORT_JOB_NOT_FOUND`
- `LEAD_IMPORT_JOB_NOT_READY`
- `LEAD_IMPORT_ROW_INVALID`
- `LEAD_EXPORT_FORBIDDEN`

## Data Model

New tables:

- `lead_import_jobs`
  - `id`, `organization_id`, `created_by_user_id`, `filename`,
    `file_sha256`, `delimiter`, `mapping_json`, `provenance_note`,
    `campaign_id`, `status`, `total_rows`, `ready_rows`,
    `duplicate_rows`, `invalid_rows`, `created_rows`, `skipped_rows`,
    `created_at`, `applied_at`
- `lead_import_rows`
  - `id`, `import_job_id`, `organization_id`, `row_number`,
    `normalized_payload_json`, `classification`, `duplicate_lead_id`,
    `error_codes_json`, `created_lead_id`, `created_at`, `updated_at`

Indexes:

- `lead_import_jobs` on `(organization_id, created_at desc)`
- `lead_import_rows` on `(import_job_id, classification, row_number)`
- `lead_import_rows` on `(organization_id, duplicate_lead_id)` for preview
  inspection

Data-handling choices:

- The first slice does not persist the raw CSV blob. It stores only the file
  hash, filename, delimiter, mapping snapshot, and normalized row payloads
  needed for preview and auditability.
- Import-row snapshots must stay organization-scoped and remain covered by the
  same lead-retention and deletion expectations already established for lead
  data.

## UI / Platform Impact

- Extend `UI-006` with an import wizard and export action.
- The wizard needs upload, mapping, preview, and apply states plus clear role
  gating for unauthorized users.
- Duplicate rows should link back to the existing matched lead where possible so
  users can inspect why the row was skipped.
- Export should reuse the currently selected lead-table filters instead of
  creating a second filter system.
- The verify script should seed a small deterministic CSV fixture with ready,
  duplicate, invalid, and formula-prefixed rows.

## Observability

- Preview creation emits an audit entry with actor, organization, filename,
  row counts, and mapping summary without raw row payload leakage.
- Apply emits an audit entry with counts for created, duplicate-skipped, and
  invalid-skipped rows.
- Export emits an audit entry with filter snapshot and exported row count.
- Import parsing and apply paths should log job id, organization id,
  classification counts, and latency, but never raw CSV contents or secret
  material.

## Alternatives Considered

1. Update-or-merge duplicates during import. Rejected because the first slice
   would widen into data-ownership conflict resolution and weaken the existing
   lead baseline.
2. Persist the raw CSV for later replay. Rejected because the product only
   needs preview evidence and auditability in the first slice, not long-lived
   artifact storage.
3. Fold lead import/export into the report-export contract from `US-019`.
   Rejected because lead-record movement has duplicate, provenance, and activity
   semantics that reporting export does not carry.
