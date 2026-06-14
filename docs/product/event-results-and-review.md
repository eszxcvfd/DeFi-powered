# Event Results And Review

Source: `SPEC.md` sections 5.5, 7.2, 8.3, 12, 14.1, `UI-003`, `UI-004`, and `UC-02`.

## Product Goal

Analysts and sales users need discovery output to become a trustworthy event
review surface rather than an opaque job artifact. The product contract must
define how LiveLead normalizes raw discovery findings into canonical event
records, preserves provenance and confidence, deduplicates repeated findings,
and exposes a minimal results list and detail view before scoring and outreach
features arrive.

## MVP Scope

This product slice covers:

- Normalizing deterministic discovery output into canonical event records.
- Preserving required provenance fields for each event and source observation,
  including source id, source URL, and observation time.
- Tracking confidence for inferred or uncertain event data rather than treating
  all fields as equally trusted.
- Deduplicating repeated findings from multiple approved sources while
  preserving linked source observations.
- Showing a minimal event results list for a campaign or discovery run.
- Showing a minimal event detail surface with overview and source-evidence
  context that later scoring and engagement stories can build on.

This product slice does not yet cover:

- Event scoring, priority ranking, or score-breakdown workflows.
- Audience hypothesis generation.
- Engagement content, review, or send flows.
- Bulk watchlist, reminders, or bulk re-score actions.
- Browser-assisted session launch from event detail.
- Calendar export, CRM export, or lead conversion workflows.

## Contract Rules

- Every canonical event must preserve at least one source observation and must
  retain the required source fields needed for review: `canonical_title`,
  `source_url`, `observed_at`, and `source_id`.
- Fields inferred, merged, or otherwise not copied directly from one source
  must stay distinguishable from directly observed fields and must carry
  confidence or equivalent trust metadata.
- Deduplication must reduce duplicate rows in the user-facing results surface
  without discarding the underlying source observations that justify the merged
  record.
- The product must keep enough provenance for a reviewer to understand which
  source or sources produced the event and when they were observed.
- Manual overrides to canonical event data are allowed only when actor and
  timestamp metadata can be preserved, even if the first UX for manual override
  remains out of scope for this story.
- Results list and detail responses must expose source evidence safely without
  leaking secrets, connector internals, or policy-protected raw credentials.
- A completed discovery job is not sufficient proof of value unless users can
  review the resulting canonical events in a stable list or detail workflow.

## API Surface

- `GET /campaigns/{id}/events`: list canonical events for a campaign, with
  support for lightweight filtering by discovery run, source, date, or status
  when available.
- `GET /events/{id}`: return canonical event detail, merged field values,
  provenance summary, and linked source observations needed for review.
- Internal discovery-to-event normalization flow must persist canonical event
  records and source observations without requiring live third-party sources.

## UI Surface

The MVP event review slice should introduce the `UI-003` and `UI-004`
direction without over-claiming later intelligence features:

- Event results table with stable rows, source badges, and confidence-aware
  summary fields.
- Minimal filtering so users can narrow recent discovery output.
- Event detail header plus overview and source-evidence content.
- Clear placeholders or deferred states for score, audience, engagement, and
  browser-assisted actions when those stories have not landed yet.

## Validation Implications

- Unit proof should cover normalization rules, deduplication heuristics, and
  provenance or confidence mapping.
- Integration proof should cover persistence of canonical events and source
  observations plus list/detail API behavior.
- E2E proof should cover reviewing results from a completed deterministic
  discovery run in the UI.
- Logs/audit proof should confirm merge or normalization decisions are
  explainable and do not leak secrets.
- Platform proof should keep event review verification wired into the Harness
  matrix for later scoring and lead workflows.
