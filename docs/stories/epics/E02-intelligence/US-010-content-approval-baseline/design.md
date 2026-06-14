# Design

## Domain Model

The story should formalize the first approval-workflow objects:

- `ContentReviewDecision`: approve or reject decision linked to a draft.
- `ContentReviewStatus`: lifecycle state for `DRAFT`, `IN_REVIEW`, `APPROVED`,
  and `REJECTED`.
- `ContentReviewerAssignment`: reviewer or equivalent review-context marker.
- `ContentRevisionMarker`: revision metadata that lets the workflow distinguish
  content edits from review decisions.

Business rules:

- A draft cannot become approved without an explicit review action.
- Review decisions must preserve actor, timestamp, resulting status, and
  optional note.
- Rejecting a draft must not destroy prior draft content or history.
- Approval and rejection should operate on the current draft revision context
  so later reviewers can see what was actually reviewed.
- Approval must not imply export, sending, or browser execution in this story.
- Authorization boundaries should ensure review actions are separate from
  general editing when the role model requires it.

## Application Flow

Commands:

- Submit or move a draft into review.
- Approve a draft.
- Reject a draft with decision note or reason.

Queries:

- Load draft detail with current review status and recent decision history.
- Load event or content-studio views with summary review state for each draft.

Approval workflow should live in domain or application layers so reviewer logic
and audit rules remain independent from UI widgets. Draft-generation logic from
`US-009` should remain separate from review transitions, with clear handoff via
draft status and revision metadata.

## Interface Contract

The minimum contract should cover:

- `POST /content/{id}/approve` and `POST /content/{id}/reject`.
- Stable payload fields for current status, reviewer context, decision note,
  timestamps, and revision markers.
- Clear error behavior for missing draft scope, invalid state transitions, and
  unauthorized review actions.

## Data Model

Expected persistence work:

- Add review-decision or review-history storage linked to generated drafts.
- Persist current draft status, reviewer identity or assignee, decision note,
  and timestamps.
- Preserve enough lifecycle metadata to support later `USED` and `ARCHIVED`
  states without implementing them fully in this story.
- Avoid pulling export or external-send tables into this story.

## UI / Platform Impact

- Extend the content-studio slice with explicit review controls and status
  badges.
- Show approval or rejection context clearly near each draft.
- Keep export, send, and usage actions visibly deferred.

## Observability

- Record submit-for-review, approve, and reject actions in structured logs or
  audit-friendly traces.
- Keep it diagnosable which reviewer acted on which draft revision.
- Ensure logs do not imply send or use actions when a draft was merely approved.

## Alternatives Considered

1. Combine approval with copy/export. Rejected because approval is a distinct
   governance boundary that should be proven before usage actions appear.
2. Treat approval as a frontend-only flag. Rejected because reviewer actions
   and audit trails need durable backend state.
