# LiveLead Product Docs

Source of truth hierarchy:

1. `SPEC.md`
2. accepted decisions in `docs/decisions/`
3. product-domain files in this directory

This directory now contains the living product contract for LiveLead, broken
into smaller domain files so future stories can update only the surfaces they
actually change.

## Core Docs

- `overview.md`: product summary, principles, roles, and non-goals.
- `mvp-scope-and-priorities.md`: seven core jobs, guardrails, and priority
  rules.
- `identity-and-access.md`: login, session, RBAC, and tenant-isolation
  contract.
- `member-management-and-access-governance.md`: invitations, role changes,
  disable/revoke rules, and admin membership governance.
- `notification-delivery-and-preferences.md`: in-app alerts, email delivery,
  and per-user notification controls.
- `campaign-and-icp.md`: campaign input, natural-language brief parsing, ICP,
  target-market mix.
- `source-registry-and-policy.md`: governed source catalog and channel policy.
- `discovery-job-lifecycle.md`: discovery launch, progress, state model, and
  structured criteria snapshots.
- `engagement-plans-and-tasks.md`: event-state-aware playbooks and task
  contracts.
- `generated-content-and-safety.md`: reviewable AI drafts and safety rules.
- `platform-and-automation-policy.md`: runtime and automation guardrails.
- `audit-log-and-governance.md`: admin audit history, redaction, and governance
  query surface.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
