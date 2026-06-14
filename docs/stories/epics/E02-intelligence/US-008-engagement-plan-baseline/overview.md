# Overview

## Current Behavior

`US-007` makes event analysis more interpretable through audience hypotheses,
but users still lack a concrete execution plan for what to do before, during,
and after an event. The event detail surface has no engagement-plan contract,
no task model, and no workflow bridge between ranked opportunities and later
content generation.

## Target Behavior

This story should establish the first engagement-planning slice after audience
analysis:

- Create an engagement plan for a scored event.
- Organize tasks into before, during, and after event phases.
- Track task status, assignee, and deadline.
- Show plan tasks in event detail.
- Preserve enough structure for later content generation and review workflows.

This story makes analysis operational. It does not yet claim AI copy
generation, reviewer approval, copy/export flows, or lead conversion behavior.

## Affected Users

- Analyst.
- Sales/BD.
- Viewer.
- Future content-review and lead-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/event-scoring-and-priority.md`
- `docs/product/audience-hypotheses-and-evidence.md`
- `docs/product/engagement-plans-and-tasks.md`

## Non-Goals

- AI-generated content variants or prompt controls.
- Approval workflow and approval-history surfaces.
- Copy/export or “used” content lifecycle.
- Automatic posting, messaging, or browser execution.
- Lead creation or pipeline-stage updates.
