# Design

## Domain Model

The story should formalize the first reviewable event domain objects:

- `Event`: canonical event record scoped for product review.
- `EventSourceObservation`: source-specific evidence linked to a canonical
  event, including source id, source URL, observation time, and source payload
  metadata.
- `EventCampaignLink` or equivalent association: links a canonical event to the
  campaign or discovery context where it was found.
- `EventMergeDecision` or equivalent internal explanation record when multiple
  findings are collapsed into one canonical event.

Business rules:

- A canonical event must not exist without at least one source observation.
- Required source-backed review fields include `canonical_title`, `source_url`,
  `observed_at`, and `source_id`.
- Inferred or merged fields must remain distinguishable from directly observed
  source fields and should carry confidence metadata.
- Deduplication may merge repeated findings into one review row, but the linked
  source observations must remain queryable for later explanation.
- Manual override support must preserve actor and timestamp metadata even if the
  first write surface is deferred.

## Application Flow

Commands:

- Normalize discovery findings into canonical events.
- Merge or create canonical events when deduplication rules trigger.
- Persist source observations and provenance metadata.

Queries:

- List campaign events and filter recent discovery results.
- Get event detail with source evidence.
- Load discovery-run-linked events for result review.

Normalization and deduplication logic should live in domain or application
layers rather than in transport handlers or UI code. Discovery orchestration
should hand off deterministic findings to an event-normalization boundary
without forcing the event domain to know queue internals.

## Interface Contract

The minimum contract should cover:

- `GET /campaigns/{id}/events` for a reviewable event list.
- `GET /events/{id}` for canonical event detail and evidence.
- Stable list fields for title, time, platform/source summary, and confidence
  signals.
- Detail fields that separate canonical values from linked source observations
  when the distinction matters to the user.

Errors should distinguish missing campaign scope, missing event, and invalid
filter usage without exposing storage internals.

## Data Model

Expected persistence work:

- Add canonical event storage with organization/campaign linkage, normalized
  event fields, confidence metadata, and timestamps.
- Add source-observation storage with source id, source URL, observation time,
  external id, raw title, content hash, and artifact references when policy
  allows.
- Add indexes or lookup strategy that support campaign-scoped event review and
  deterministic deduplication checks.
- Keep future scoring, watchlist, and lead-pipeline tables out of this story
  unless they are strictly needed as foreign-key placeholders.

## UI / Platform Impact

- Add a results table reachable after discovery runs or from campaign context.
- Add a minimal event detail view with source evidence.
- Keep score, audience, engagement, and browser actions clearly deferred.
- Avoid UI-only deduplication that would leave API and persistence inconsistent.

## Observability

- Record normalization and merge decisions in structured logs or audit-friendly
  traces.
- Keep provenance decisions explainable when two findings collapse into one
  canonical event.
- Ensure secret-bearing source metadata stays redacted in logs and UI payloads.

## Alternatives Considered

1. Keep discovery output as raw per-source rows and defer canonical events
   entirely. Rejected because later scoring, watchlist, and lead stories need a
   stable event identity first.
2. Deduplicate only in the UI while leaving duplicate persistence untouched.
   Rejected because it would make review, scoring, and audit behavior diverge.
