# 0016 Event Manual Overrides Baseline

Date: 2026-06-16

## Status

Accepted

## Context

LiveLead already normalizes deterministic discovery output into canonical
events, persists source observations, and shows event list and detail
surfaces with confidence-aware provenance. `US-005` and `US-006` shipped the
review surface, but reviewers still cannot correct canonical event data
when normalization is wrong or source quality is incomplete. `SPEC.md`
section 5.5 (FR-NOR-006) requires authorized manual edits, manual
overrides must be protected from automatic overwrite, and section 5.6
(FR-EVT-004) requires event detail history.

The change touches authorization (only certain roles can edit), audit
and security (every edit must leave actor/timestamp evidence), data
model (new override and history tables), public API contract (new
PATCH and clear-override endpoints, extended detail payload), and
existing behavior (downstream score and watchlist views must keep
working). The work is high-risk.

## Decision

`US-031` introduces the first canonical event manual-override slice:

- A new `event_manual_overrides` durable record holds per-organization,
  per-event, per-field override metadata with a source-backed baseline
  value, the current manual value, actor id, actor role, and the
  override state. The unique key is `(organization_id, event_id, field)`
  so a field can have at most one active override per event.
- A new `event_change_history` record holds append-only edit and
  clear-override rows with actor id, actor role, field, prior value,
  new value, and reason. New rows are never updated or deleted by
  product code.
- The bounded editable field allowlist is
  `canonical_title`, `description`, `organizer`, `region`, `starts_at`,
  and `source_url`. `id`, `organization_id`, `campaign_id`,
  `observed_at`, and `discovery_job_id` remain immutable because they
  are part of the provenance chain.
- Only `OWNER`, `ADMIN`, and `ANALYST` may edit canonical fields.
  `SALES_BD`, `REVIEWER`, `COMPLIANCE`, and `VIEWER` are denied. The
  rule mirrors `can_edit_campaign` so the existing RBAC boundary
  treats event-data editing the same as campaign editing.
- Source observations remain immutable. A manual override stores the
  latest source-backed baseline value in the override row so the
  baseline can be restored exactly when the override is cleared,
  even if a later merge rewrites the canonical row.
- The normalization ingest path in
  `application/events/ingest.py` is extended so the merge step does
  not overwrite a field that is currently protected by a manual
  override. Unprotected fields still update, and a structured
  `protected_field_skipped` log line is emitted with the event id,
  field, and current manual value.
- The REST surface is `PATCH /events/{id}` (allowed-field updates),
  `POST /events/{id}/overrides/{field}/clear` (clear one override),
  and `GET /events/{id}/history` (timeline view). The
  `GET /events/{id}` response now includes an
  `EventFieldProvenance` summary that reports the list of overridden
  fields with actor, role, and timestamp.
- The new `AuditAction` values are
  `event.override.upserted`, `event.override.cleared`, and
  `event.override.denied`. The `event` target type covers the
  override entry; existing audit redaction rules already keep the
  override note free of credentials.
- The React event detail surface gains an `EventOverridePanel` and an
  `EventHistoryPanel`. The `EventDetailPage` shows an override badge
  per field and a clear-override control when a manual value is
  active. The watched-events and engagement-plan surfaces are not
  touched in this slice.

## Alternatives Considered

1. Mutate the canonical event row directly without storing an
   override record. Rejected because later rediscovery would
   silently erase manual corrections, and there would be no way to
   tell which fields are source-backed.
2. Let users edit raw source observations. Rejected because source
   observations are immutable provenance evidence, and editing
   them would corrupt the audit chain.
3. Allow `SALES_BD` to edit organizer and timing fields. Rejected
   because the existing campaign-edit RBAC places
   `SALES_BD` below `ANALYST`; the slice keeps that boundary to
   avoid widening the editable surface.
4. Skip change history and only store the latest override value.
   Rejected because `SPEC.md` requires actor and timestamp
   tracking and the event-detail history section.
5. Approve each edit through a reviewer workflow. Rejected because
   the product doc explicitly defers field-level approval to a
   later story; this slice trusts the role boundary.

## Consequences

Positive:

- Analysts and admins can correct normalized data without breaking
  the source-provenance chain.
- The event detail surface explains which fields differ from the
  source-backed value, so reviewers understand the difference.
- Automatic normalization cannot silently overwrite a manual
  correction; structured logs explain every protected-field skip.
- The change history is append-only and audit-safe, satisfying
  `SPEC.md` FR-NOR-006 and FR-EVT-004 history requirements.

Tradeoffs:

- The editable field set is bounded. Future fields must be added
  through a follow-up decision record and the field allowlist.
- Clearing an override restores the value stored in the override
  row, not a freshly recomputed source value. The baseline value
  is captured at override time, which matches the source-backed
  canonical state at that moment.
- Existing score, reminder, and watchlist views may show stale
  derived data until a downstream refresh runs. The event detail
  surface advertises the current effective values; downstream
  read-model freshness remains a per-feature concern.

## Follow-Up

- A bulk-edit story should reuse the same `event_manual_overrides`
  table but operate over many events in one audited transaction.
- A field-level approval workflow story should add a `pending`
  state to the override record without redefining the contract.
- The downstream score freshness story should subscribe to
  `event_change_history` and trigger a re-score when an
  override that influences scoring is applied or cleared.
- A calendar export story should reuse
  `event_manual_overrides.starts_at` so calendar sync never
  silently overwrites a manual start time.
