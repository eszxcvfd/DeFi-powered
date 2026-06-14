# Overview

## Current Behavior

`US-010` gives generated drafts a formal approval workflow, but the product
still has no governed handoff path after approval. Users cannot safely copy or
export approved content through the product, and there is no lifecycle
distinction between approved content that is merely ready and content that has
actually been used downstream.

## Target Behavior

This story should establish the first approved-content handoff slice:

- Allow copy/export for approved content.
- Mark approved content as used after deliberate handoff.
- Preserve handoff audit metadata.
- Show status that distinguishes approved from used content.

This story makes approved content actionable. It does not yet claim
browser-assisted sending, automatic posting, archival workflow, or downstream
lead automation.

## Affected Users

- Analyst.
- Sales/BD.
- Reviewer.
- Future browser-send and archive-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/generated-content-and-safety.md`
- `docs/product/content-approval-and-review.md`
- `docs/product/content-handoff-and-export.md`

## Non-Goals

- Browser-assisted or automatic sending.
- `ARCHIVED` lifecycle behavior.
- Usage analytics dashboards.
- Lead creation or pipeline changes.
- Bulk publishing workflows.
