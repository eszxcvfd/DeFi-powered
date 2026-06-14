# Overview

## Current Behavior

`US-008` gives users a structured engagement plan, but there is still no
content-studio slice that turns those tasks into concrete draft copy. The
product has no generated-content contract, no variant generation flow, no
visible generation context, and no safety-flag surface for draft content.

## Target Behavior

This story should establish the first generated-content slice after engagement
planning:

- Generate multiple draft variants from event and plan context.
- Let users choose content type, platform, language, tone, length, and CTA.
- Show the context that is sent for generation.
- Persist generation metadata and editable draft content.
- Surface risk flags before approval workflow exists.

This story makes planning draftable. It does not yet claim reviewer approval,
copy/export, used lifecycle, or external sending behavior.

## Affected Users

- Analyst.
- Sales/BD.
- Reviewer.
- Future approval and export-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/engagement-plans-and-tasks.md`
- `docs/product/generated-content-and-safety.md`

## Non-Goals

- Reviewer approval workflow or approval history.
- Copy/export and “used” lifecycle behavior.
- Automatic posting or browser-assisted sending.
- Prompt-learning or autonomous prompt optimization.
- Lead creation or pipeline changes.
