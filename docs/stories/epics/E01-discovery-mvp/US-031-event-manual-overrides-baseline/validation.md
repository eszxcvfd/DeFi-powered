# Validation

## Proof Strategy

This story is done only when LiveLead can preserve authorized manual event
corrections, show event change history, protect active overrides from automatic
overwrite, and keep source provenance explainable through the event detail
workflow.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Field allowlist validation, override-protection rules, clear-override restoration, and event-history assembly. |
| Integration | Event edit persistence, change-history queries, authorization enforcement, and normalization behavior that skips protected fields. |
| E2E | Authorized user edits an event field, sees override provenance and history, clears the override, and confirms the source-backed value returns in the detail view. |
| Platform | Story verification command proves backend, frontend, and auth-aware event-edit fixtures succeed without weakening event-review or score/watchlist proof paths. |
| Performance | Event-detail and history queries remain bounded for normal event volumes and repeated edits to one event. |
| Logs/Audit | Edit, clear-override, denied-edit, and protected-field-skip paths remain explainable with actor, event, field, and timestamp context. |

## Fixtures

- At least one authenticated user with permission to edit canonical events.
- One user without edit permission to prove denial behavior.
- One canonical event with source-backed values suitable for time, URL, and
  organizer-style edits.
- One rediscovery or normalization fixture that attempts to write a protected
  field after a manual override is active.

## Commands

```text
TBD
```

Planned proof should eventually include:

- unit tests for event override and history rules
- integration tests for event edit APIs and normalization protection
- one frontend e2e scenario for edit, history, and clear-override flow
- `scripts/bin/harness-cli story verify US-031` after a verification command is
  added

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-031` once implemented with
  the expected proof columns populated.
- A representative e2e run covers edit, history visibility, clear override, and
  denied edit behavior.
- Integration proof confirms a later normalization attempt does not silently
  overwrite a protected manual field.
