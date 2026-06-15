# Overview

## Current Behavior

LiveLead already relies on auditability in many implemented slices, but there is
no dedicated product contract or story packet for a central audit log. The repo
does not yet define a first-class admin audit surface, a normalized event shape,
or a durable tenant-scoped query model for who did what across login, policy,
content, browser, and lead workflows.

## Target Behavior

This story should establish the first audit-log governance slice for LiveLead:

- A tenant-scoped, append-only audit event model for sensitive and contract-
  relevant actions.
- A secret-safe admin read surface for filtering and inspecting audit entries.
- Consistent capture of actor, action, target, result, timing, and request or
  session context.
- Clear denied, failed, cancelled, and system-triggered audit outcomes, not only
  successful actions.
- A stable contract that later retention-policy, data-deletion, connector-
  health, and auth-management stories can extend without redefining audit
  basics.

## Affected Users

- Owner/Admin operators who need governance visibility across the product.
- Security or compliance-minded reviewers who need trustworthy action history.
- Future implementation agents extending auth, retention, deletion, or
  observability behavior.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/audit-log-and-governance.md`

## Non-Goals

- Retention-policy editing or cleanup jobs.
- Data deletion or anonymization workflows.
- Connector-health analytics dashboards.
- Full member-management UX or SSO administration.
- External SIEM export or webhook delivery.
