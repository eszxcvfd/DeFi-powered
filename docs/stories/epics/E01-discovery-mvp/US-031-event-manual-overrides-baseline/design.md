# Design

## Domain Model

The story should formalize the first governed event-edit objects:

- `EventManualOverride`: field-scoped override metadata linked to one canonical
  event, one organization, and one actor.
- `EventChangeHistoryEntry`: append-only record for edit and clear actions with
  actor, timestamp, field, prior value, resulting value, and optional reason.
- `EventFieldProvenance`: projection helper that explains whether a current
  canonical field comes from source normalization or manual override.

Business rules:

- Source observations stay immutable; manual override changes the effective
  canonical event field only.
- Only an allowed field set may be edited in this baseline.
- A manual override remains active until cleared explicitly.
- Later normalization or rediscovery must not overwrite an active manual field.
- Clearing an override restores the latest source-backed canonical value.
- History entries remain append-only even when a field is edited multiple times.

## Application Flow

- `UpdateCanonicalEventFields` validates field allowlist, authorization, and
  current event scope, then applies manual-override semantics.
- `ClearCanonicalEventOverride` removes one active manual field override and
  restores the source-backed effective value.
- `ListEventChangeHistory` returns timeline-ready change records for one event.
- `ProjectEventFieldProvenance` enriches event detail responses with override
  state and source-versus-manual summary.
- `ProtectManualFieldsDuringNormalization` ensures rediscovery writes skip
  currently protected fields while still updating unprotected canonical data.

## Interface Contract

Backend contract should minimally support:

- `PATCH /events/{id}` for allowed canonical field overrides.
- `POST /events/{id}/overrides/{field}/clear` or equivalent clear action.
- `GET /events/{id}` with field-provenance or override-summary metadata.
- `GET /events/{id}/history` for event change history.

Expected payload concerns:

- Event edit payloads should reject unsupported fields and invalid value shapes
  clearly.
- Detail responses should expose enough provenance metadata for the UI to show
  overridden fields without dumping raw protected source payloads.
- Unauthorized edit attempts must fail safely and auditably.

## Data Model

- Add durable override and change-history storage keyed by organization, event,
  field, and actor.
- Preserve enough source-backed canonical data to restore values when an
  override is cleared.
- Add indexes for event-detail history reads and active-override lookups during
  normalization.
- Keep future merge/split or bulk-edit semantics out of this baseline unless a
  schema placeholder is strictly required.

## UI / Platform Impact

- Extend event detail with bounded edit controls for allowed canonical fields.
- Show override badges or equivalent provenance indicators on edited fields.
- Add event-history surface with actor and timestamp context.
- Add clear-override control for active manual fields.
- Keep results-table bulk editing and admin-style maintenance controls out of
  the first UX.

## Observability

- Record audit entries for event edit and clear-override actions.
- Emit structured diagnostics when normalization skips protected fields or when
  edit validation fails.
- Preserve correlation between event id, actor id, changed fields, and history
  entries for support/debugging.

## Alternatives Considered

1. Mutate canonical event rows directly without explicit override metadata.
   Rejected because later rediscovery could silently erase manual corrections.
2. Let users edit raw source observations instead of canonical fields. Rejected
   because source evidence should remain immutable provenance.
3. Defer event history and keep only the latest override values. Rejected
   because `SPEC.md` explicitly requires actor/timestamp tracking and event
   detail history.
