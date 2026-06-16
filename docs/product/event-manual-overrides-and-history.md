# Event Manual Overrides And History

Source: `SPEC.md` sections 5.5, 5.6, 8.3, 12, `UI-004`, and `UC-02`.

## Product Goal

Analysts and sales users need a governed way to correct canonical event data
when normalization or source quality is incomplete. The product contract must
define how LiveLead lets an authorized user override selected canonical event
fields, preserves actor and timestamp history for every change, and protects
approved manual corrections from being silently overwritten by later automatic
normalization.

## MVP Scope

This product slice covers:

- Editing a bounded set of canonical event fields from the event detail
  workflow.
- Preserving append-only change history with actor, timestamp, field, and
  before/after context.
- Showing which current event values come from manual override versus source or
  normalization output.
- Clearing a manual override so the canonical field can fall back to the
  latest normalized source-backed value.
- Protecting manually overridden fields from later automatic overwrite until
  the override is cleared.
- Showing change history in the event detail surface so reviewers can
  understand why a canonical value differs from source observations.

This product slice does not yet cover:

- Bulk event editing from list views.
- Merge, split, or archive operations for canonical events.
- Editing raw source observations or provider payloads directly.
- Field-level approval workflow for event edits.
- Automatic learning that changes normalization rules from edit history alone.
- Calendar export or cross-system synchronization.

## Contract Rules

- Source observations remain immutable evidence. Manual override changes the
  effective canonical field value, not the stored source observation itself.
- Only authorized users may edit canonical event fields; viewer-style roles
  must not gain edit capability through this baseline.
- Every manual override or clear action must preserve actor and timestamp
  metadata, and should retain the prior effective value needed for history
  review.
- Overridden fields must stay protected from later automatic normalization or
  rediscovery writes until the override is explicitly cleared.
- Clearing an override must restore the effective canonical value from the
  latest normalized source-backed state rather than inventing a new value.
- Event detail must make the difference between source-backed values and manual
  override values explainable to the user.
- Event change history must be scoped to one canonical event and remain
  queryable without leaking protected source payloads or credentials.
- When an override changes fields that influence score, time-based reminders,
  or downstream event read models, those dependent views must either recompute
  from the effective canonical value or show that freshness is pending; they
  must not silently present stale derived data as current truth.

## API Surface

- `GET /events/{id}`: include current manual-override metadata or equivalent
  field provenance summary in event detail responses.
- `PATCH /events/{id}`: update allowed canonical event fields through manual
  override semantics.
- `POST /events/{id}/overrides/{field}/clear` or equivalent action: clear one
  manual override and restore source-backed canonical behavior.
- `GET /events/{id}/history`: return change history entries for canonical event
  edits and override-clear actions.

## UI Surface

The first manual-override slice should extend the event detail workflow:

- Edit controls for the bounded set of canonical event fields.
- Clear indication when a field is manually overridden.
- Event history section or tab with actor, time, field, and change summary.
- Clear-override control for fields currently locked by manual edits.
- Validation feedback for malformed times, URLs, or unsupported field updates.

## Validation Implications

- Unit proof should cover override-protection rules, clear-override fallback,
  field-allowlist validation, and change-history assembly.
- Integration proof should cover event edit persistence, history queries,
  current-user authorization enforcement, and rediscovery-safe overwrite
  protection.
- E2E proof should cover editing an event field, seeing override badges or
  history, clearing an override, and verifying the detail view reflects the
  restored canonical value.
- Logs or audit proof should confirm who changed or cleared an override, which
  event and field were affected, and when the change happened.
- Platform proof should keep the manual-override verification path wired into
  the Harness matrix before bulk edit, calendar export, or advanced
  synchronization stories build on it.
