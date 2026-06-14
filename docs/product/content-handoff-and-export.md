# Content Handoff And Export

Source: `SPEC.md` sections 5.9, 7.2, 12, `UI-005`, and `UC-03`.

## Product Goal

Sales and analyst users need a safe way to take approved content out of the
review workflow and use it in human-controlled channels. The product contract
must define how LiveLead lets users copy or export approved content, records
that handoff, and distinguishes approved-but-unused content from content that
has already been taken into real-world workflow.

## MVP Scope

This product slice covers:

- Copying approved content from the content-studio surface.
- Exporting approved content to supported offline formats such as Markdown or
  CSV.
- Marking approved content as used or handed off after a user copies or exports
  it.
- Preserving audit metadata for handoff actions and usage-state changes.
- Showing content status that distinguishes approved content from already-used
  content.

This product slice does not yet cover:

- Browser-assisted or automatic sending.
- `ARCHIVED` lifecycle workflow.
- Full analytics on downstream usage effectiveness.
- Lead creation or pipeline actions triggered by content usage.
- Bulk external publishing or messaging.

## Contract Rules

- Only approved content may be copied or exported as ready-for-use material.
- Export and copy actions must preserve enough audit metadata to explain who
  performed the handoff and when.
- Usage-state changes must be explicit; copying or exporting should not be
  silently ignored if the product claims the content was used.
- The first handoff slice may support a minimal `USED` transition, but it must
  not imply that the system sent or posted the content itself.
- Export formats must avoid leaking hidden reviewer-only metadata or internal
  secrets not intended for downstream users.
- Approved-but-unused and used content must remain distinguishable in both UI
  and API payloads.

## API Surface

- `POST /content/{id}/mark-used`: mark approved content as used or handed off.
- Approved-content payloads must expose copy/export availability, current usage
  status, and latest handoff metadata.
- Export endpoints or equivalent download flows must only expose approved
  content and supported export formats.

## UI Surface

The MVP handoff slice should extend `UI-005` without claiming external-send
automation:

- Copy action for approved content.
- Export action for approved content.
- Visible status that distinguishes approved from used.
- Handoff history or latest usage marker visible in content detail.

## Validation Implications

- Unit proof should cover lifecycle guards for export eligibility and used-state
  transitions.
- Integration proof should cover export gating, mark-used persistence, and
  approved-only handoff behavior.
- E2E proof should cover approving content, copying or exporting it, and seeing
  used-state feedback.
- Logs or audit proof should confirm who copied, exported, or marked content as
  used.
- Platform proof should keep handoff verification wired into the Harness matrix
  before any later browser-send or archive stories.
