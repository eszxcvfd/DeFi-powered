# Overview

## Current Behavior

LiveLead already turns discovery output into canonical events, shows source
evidence, scores events, and now supports user-scoped watchlists. However,
reviewers still cannot correct canonical event data when normalization or
source quality is wrong. `SPEC.md` requires manual override actor and timestamp
tracking, and event detail also calls for change history, yet there is no
dedicated product contract or story packet for governed event edits.

## Target Behavior

This story should establish the first canonical-event manual-override slice for
LiveLead:

- Let an authorized user edit a bounded set of canonical event fields.
- Preserve append-only change history with actor, timestamp, field, and value
  transitions.
- Show which current event values come from manual override versus normalized
  source-backed data.
- Let a user clear an override so the field returns to the latest
  source-backed canonical value.
- Prevent later automatic normalization from silently overwriting protected
  manual fields.

This story should make event review trustworthy without turning the event
surface into a bulk data-maintenance console or a full event-mastering system.

## Affected Users

- Analysts who validate discovered event data before downstream outreach or
  scoring decisions.
- Sales/BD users who need trustworthy event timing, platform, and organizer
  details.
- Future implementation agents extending bulk edit, calendar export, or
  advanced event synchronization on top of a stable override contract.

## Affected Product Docs

- `docs/product/event-results-and-review.md`
- `docs/product/event-manual-overrides-and-history.md`

## Non-Goals

- Bulk event editing from results tables.
- Event merge, split, archive, or delete workflows.
- Editing raw source observations directly.
- Field-level approval workflow for event edits.
- Calendar export or external sync.
