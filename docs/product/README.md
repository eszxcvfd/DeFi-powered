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
- `scheduled-discovery-and-sync.md`: first bounded recurring discovery contract
  with scheduler dispatch and overlap guardrails.
- `query-expansion-and-review.md`: first governed discovery-query expansion
  contract with grouped variants and approval-required AI suggestions.
- `discovery-copilot-and-structured-briefing.md`: first governed natural-
  language discovery-copilot contract with structured grounded responses.
- `ai-feedback-and-learning-signals.md`: first governed AI-feedback contract for
  discovery-copilot and audience-analysis outputs without auto-learning.
- `feedback-learning-and-scoring-suggestions.md`: first governed scoring-weight
  suggestion contract derived from feedback signals with explicit approval.
- `real-environment-cutover-and-live-operations.md`: first governed pilot-live
  cutover contract for running the system in a real environment beyond test-only
  proof.
- `live-feed-and-api-discovery.md`: first real external `API`/`RSS`/`ICS`
  discovery contract and safe canonical-event ingestion.
- `public-website-playwright-discovery.md`: first governed `Playwright`
  website-discovery contract and browser-recipe extraction baseline.
- `selenium-and-alternate-adapter-discovery.md`: first governed `Selenium` or
  alternate-adapter discovery contract and engine-selection baseline.
- `event-manual-overrides-and-history.md`: authorized canonical-event edits,
  overwrite protection, and event change history.
- `event-watchlist-and-reminders.md`: user-scoped watched events, reminder
  scheduling, and saved-event revisit workflow.
- `engagement-plans-and-tasks.md`: event-state-aware playbooks and task
  contracts.
- `generated-content-and-safety.md`: reviewable AI drafts and safety rules.
- `platform-and-automation-policy.md`: runtime and automation guardrails.
- `audit-log-and-governance.md`: admin audit history, redaction, and governance
  query surface.

## Runtime and operators

- Environment template: repo-root `.env.example` (full `LIVELEAD_*` list).
- Copilot (Gemini), query expansion, and verify commands:
  `docs/RUNTIME_CONFIGURATION.md`.
- Local processes and browser/discovery flags: `docs/FOUNDATION_RUNTIME.md`.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
