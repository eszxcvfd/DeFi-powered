# Lead Import Export

Source: `SPEC.md` sections 5.11, 7.2, 12, `UI-006`, `UC-05`, and `FR-LEAD-007`.

## Product Goal

Sales and analyst users need a governed way to move lead data into and out of
LiveLead without bypassing duplicate guardrails, provenance expectations, or
tenant safety. The first import/export slice should let a user preview a CSV,
map incoming columns to the bounded lead contract, understand what will be
created or skipped, and then apply the import with durable audit evidence. The
same slice should let users export the current lead list to CSV without leaking
hidden fields or weakening permission checks.

## MVP Scope

This product slice covers:

- Exporting the current lead list to CSV using the same filter semantics as the
  lead table.
- Uploading a UTF-8 CSV with a header row and previewing it before import.
- Mapping CSV columns to a bounded lead field set.
- Reusing the existing duplicate-detection rules from the lead baseline so the
  preview can classify rows as ready, duplicate, or invalid before any write.
- Requiring a job-level provenance note so imported leads still explain where
  they came from even when the CSV has no event-linked origin.
- Applying the import as a bounded create-only operation that creates only
  preview rows classified as ready.
- Recording import and export audit entries with secret-safe payloads and
  summary counts.

This product slice does not yet cover:

- CRM synchronization, webhook-driven ingest, or bidirectional external sync.
- XLSX, Google Sheets, or arbitrary file-format support.
- Auto-merge or in-place update of existing leads during import.
- Bulk delete, bulk reassignment, or enrichment during import.
- Scheduled export delivery, report bundles, or external storage artifact
  management.

## Contract Rules

- Import and export are organization-scoped and must never cross tenant
  boundaries.
- A preview must occur before apply. The product must not create leads directly
  from an uploaded CSV in one step.
- The import surface is create-only in the first slice. Duplicate rows are
  surfaced during preview and skipped during apply; they are not merged or
  overwritten.
- Every imported lead must preserve provenance by carrying either mapped source
  fields from the CSV or the required job-level provenance note entered during
  preview.
- The import field mapper must support only the bounded lead fields already
  accepted by the lead domain: display name, company or organization, title,
  public URL, source note, related campaign, interests, pain points, owner,
  status, lawful-basis note, follow-up date, and notes.
- The first import slice requires `display_name` and at least one of
  `company_name`, `public_profile_url`, or the job-level provenance note so the
  record is reviewable after import.
- Export must escape spreadsheet-formula prefixes (`=`, `+`, `-`, `@`) so CSV
  downloads do not introduce formula-injection risk when opened in spreadsheet
  tools.
- Hidden or internal-only fields such as secret references, raw duplicate-match
  heuristics, or internal notes that the lead list does not expose must not
  appear in exported CSV output.
- Import validation errors must stay row-specific and reviewable in the preview;
  the user should never receive only a generic file-level failure when some rows
  are valid and others are not.

## API Surface

- `POST /leads/imports:preview`: upload CSV, mapping payload, optional campaign
  context, and required provenance note; return a preview job id plus row
  counts.
- `GET /leads/imports/{id}`: return preview-job summary, mapping snapshot,
  provenance note, and ready or duplicate or invalid counts.
- `GET /leads/imports/{id}/rows?status=&limit=&offset=`: return paginated row
  preview details including normalized values, duplicate-match summary, and
  validation errors.
- `POST /leads/imports/{id}:apply`: create leads for rows currently marked
  ready, skip duplicate or invalid rows, append lead activity entries for each
  created record, and return an apply summary.
- `GET /leads/export.csv?...`: return a CSV for the current lead filter set
  using the same organization scope and visible columns as the lead table.

## UI Surface

The first `UI-006` extension should remain bounded:

- An import action in the lead workspace that opens a wizard with upload,
  mapping, preview, and apply steps.
- A preview summary that clearly shows how many rows are ready, duplicate,
  invalid, created, or skipped.
- A per-row review table for invalid and duplicate rows with searchable error
  messages and duplicate-match references.
- An export action that respects the current lead-table filters and downloads a
  CSV immediately.
- Clear role-gate messaging when a viewer or reviewer reaches import or export
  controls without permission.

## Validation Implications

- Unit proof should cover CSV parsing, field mapping, required-field rules,
  duplicate classification, formula escaping, and create-only apply behavior.
- Integration proof should cover preview persistence, organization scoping,
  apply summaries, activity creation, and export shape.
- E2E proof should cover importing a mixed CSV with ready, duplicate, and
  invalid rows, then exporting the filtered lead list.
- Security proof should cover CSV formula escaping, unauthorized access denial,
  tenant isolation, and secret-safe audit payloads.
- Platform proof should keep the verify command and any preview fixtures wired
  into the Harness matrix.
