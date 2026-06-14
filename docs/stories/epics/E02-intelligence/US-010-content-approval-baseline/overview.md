# Overview

## Current Behavior

`US-009` lets users generate and edit draft variants, but the product still
has no formal approval workflow that separates drafting from reviewed content.
There is no reviewer decision surface, no approve or reject state transition,
and no contract that makes approved content meaningfully distinct from ordinary
drafts.

## Target Behavior

This story should establish the first approval slice after generated drafts:

- Move drafts through explicit review states.
- Let reviewers approve or reject drafts.
- Record reviewer identity, timestamps, and decision notes.
- Show review state and recent approval context in the content studio.
- Enforce that only approved drafts are considered ready for later use.

This story makes generated content governable. It does not yet claim
copy/export actions, used lifecycle, archival, or external sending behavior.

## Affected Users

- Analyst.
- Sales/BD.
- Reviewer.
- Future export and content-usage implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/generated-content-and-safety.md`
- `docs/product/content-approval-and-review.md`

## Non-Goals

- Copy/export and “used” lifecycle behavior.
- Archival workflow.
- Automatic posting or browser-assisted sending.
- Reviewer analytics dashboards.
- Lead creation or pipeline changes.
