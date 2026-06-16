# Overview

## Current Behavior

LiveLead now covers manual discovery jobs plus the three experimental connector
families needed to find real events from feeds/APIs, `Playwright` websites, and
`Selenium`/alternate adapters. However, discovery still depends on a person to
launch each run manually. `SPEC.md` requires bounded scheduling support, yet the
product does not have a dedicated contract or story packet for recurring
discovery runs, next-run previews, or pause/resume behavior.

## Target Behavior

This story should establish the first scheduled-discovery slice for LiveLead:

- Let users create bounded recurring discovery schedules for valid campaigns and
  approved source selections.
- Support daily, weekly, and restricted-cron recurrence with timezone-aware
  next-run preview.
- Dispatch scheduled runs through the same governed discovery job pipeline used
  for manual execution.
- Prevent unsafe overlap and keep policy/quota checks active at execution time.
- Show schedule status, next run, latest run result, and pause/resume controls.

This story should add repeatable discovery without jumping ahead to AI query
expansion, discovery copilot Q&A, complex calendar rules, or scheduled report
delivery.

## Affected Users

- Analysts who want discovery to refresh automatically for important campaigns.
- Owners/Admins who need bounded scheduling and clear pause/disable controls.
- Future implementation agents extending query expansion, discovery copilot, or
  incremental sync on top of a stable scheduling contract.

## Affected Product Docs

- `docs/product/discovery-job-lifecycle.md`
- `docs/product/scheduled-discovery-and-sync.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- AI query expansion before scheduled runs.
- Discovery copilot question/answer workflows.
- Complex calendars, blackout windows, or holiday rules.
- Scheduled report/email digest delivery.
- Full incremental sync cursor management.
