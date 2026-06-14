# Design

## Domain Model

The story should formalize the first handoff-workflow objects:

- `ContentUsageState`: lifecycle marker for at least `APPROVED` and `USED`.
- `ContentHandoffRecord`: audit-friendly record for copy, export, or mark-used
  actions.
- `ContentExportFormat`: supported export targets such as Markdown or CSV.
- `ContentHandoffActor`: actor metadata that explains who performed the
  handoff.

Business rules:

- Only approved content may be copied, exported, or marked used as ready
  content.
- Marking content as used must not imply the system sent or posted it.
- Handoff actions must preserve actor and timestamp metadata.
- Export output must filter out internal-only review metadata that should not
  travel downstream.
- Used-state transitions should remain reversible only if the product later
  defines such behavior; this story should not silently invent reverse states.

## Application Flow

Commands:

- Copy approved content.
- Export approved content in a supported format.
- Mark approved content as used after a deliberate handoff action.

Queries:

- Load draft detail with usage status and recent handoff metadata.
- Load content-studio lists with approved or used status summaries.

Handoff logic should remain separate from approval logic so reviewer actions and
usage actions stay distinguishable in audit trails. Export generation should sit
behind application boundaries rather than being a UI-only string formatter.

## Interface Contract

The minimum contract should cover:

- `POST /content/{id}/mark-used`.
- Approved-content export or download flow with explicit format selection.
- Stable payload fields for approval status, usage status, latest handoff
  timestamp, actor, and available export formats.
- Clear error behavior for unapproved content, invalid format requests, and
  invalid usage transitions.

## Data Model

Expected persistence work:

- Add usage-state or handoff-history storage linked to generated drafts.
- Persist export actions, mark-used events, actor, timestamps, and format when
  relevant.
- Preserve compatibility with later `ARCHIVED` or send-lifecycle work.
- Avoid pulling browser-send or lead tables into this story.

## UI / Platform Impact

- Extend content-studio views with copy/export controls for approved content.
- Show used-state badges or equivalent status markers.
- Provide feedback after copy/export or mark-used actions.
- Keep external-send and archive actions visibly deferred.

## Observability

- Record copy, export, and mark-used events in structured logs or audit-friendly
  traces.
- Keep it diagnosable which approved revision was handed off.
- Ensure exported files or logs do not expose hidden internal-only review data.

## Alternatives Considered

1. Skip explicit handoff tracking and rely only on users copying text manually.
   Rejected because the product would then lose auditability at the point where
   approved content leaves the system.
2. Jump straight from approval to browser-assisted sending. Rejected because
   human-controlled handoff is the safer MVP bridge before external execution.
