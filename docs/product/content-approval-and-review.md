# Content Approval And Review

Source: `SPEC.md` sections 5.9, 7.2, 12, `UI-005`, and `UC-03`.

## Product Goal

Analyst, sales, and reviewer users need draft content to move through a clear
review workflow before it is considered safe to use. The product contract must
define how LiveLead routes generated drafts into review, records approve or
reject decisions, preserves revision and decision history, and enforces the
rule that only approved content can become ready for later use.

## MVP Scope

This product slice covers:

- Moving generated drafts through a review lifecycle.
- Supporting at least `DRAFT`, `IN_REVIEW`, `APPROVED`, and `REJECTED`
  lifecycle states in the first approval slice.
- Assigning review responsibility or equivalent reviewer context.
- Recording approve or reject decisions with decision metadata and comments.
- Showing review status and recent decision history in the content-studio
  surface.
- Enforcing that unapproved drafts are not presented as ready for later use.

This product slice does not yet cover:

- Copy/export actions.
- `USED` or `ARCHIVED` lifecycle transitions.
- Automatic posting, browser-assisted sending, or any external execution.
- Full analytics on reviewer throughput or SLA.
- Lead conversion or pipeline updates.

## Contract Rules

- Generated content starts as draft material and must not be treated as ready
  for later use until it is approved.
- Review actions must preserve actor, timestamp, status change, and optional
  reviewer notes for auditability.
- Rejecting a draft must keep the draft and its decision history visible rather
  than silently deleting it.
- Approval workflow must distinguish draft editing from formal review actions so
  later audit can explain who edited versus who approved.
- Reviewer-facing state must be explicit in the UI and API; hidden workflow
  assumptions are not sufficient.
- The first approval slice may stop at `APPROVED` or `REJECTED`, but it must
  leave a clean path for later `USED` and `ARCHIVED` transitions.
- Approval must not imply sending, export, or browser execution in this story.

## API Surface

- `POST /content/{id}/approve`: approve a draft and record reviewer metadata.
- `POST /content/{id}/reject`: reject a draft and record reviewer metadata and
  reason.
- Draft payloads must expose current status, reviewer or assignee context,
  latest decision metadata, and revision markers needed for review.

## UI Surface

The MVP approval slice should deepen `UI-005` without claiming export or send
behavior:

- Review status badges for drafts.
- Reviewer decision controls for approve or reject.
- Reviewer note or rationale field.
- Approval-history or recent decision context sufficient to understand the
  latest workflow state.

## Validation Implications

- Unit proof should cover state transitions, allowed actions by state, and
  reviewer decision rules.
- Integration proof should cover approval and rejection persistence plus API
  behavior.
- E2E proof should cover moving a draft into review and completing approve or
  reject actions in the UI.
- Logs or audit proof should confirm who approved or rejected what and when.
- Platform proof should keep approval verification wired into the Harness
  matrix for later export and used-lifecycle stories.
