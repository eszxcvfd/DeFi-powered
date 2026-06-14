# Exec Plan

## Goal

Define the first governed browser-debug-artifact slice so supervised browser
sessions can capture screenshot, console-log, and trace artifacts with clear
access and retention guardrails, without widening into profile management or
compliance-only browser modes.

## Scope

In scope:

- Opt-in debug capture for supervised browser sessions.
- Manual screenshot capture from the browser session console.
- Automatic console-log and trace artifact capture when debug is enabled.
- Durable artifact metadata, authorized retrieval, and retention expiry rules.
- Audit visibility for debug enablement, capture requests, artifact access, and
  expiration or deletion outcomes.

Out of scope:

- Browser profile lifecycle create, lock, expire, or delete flows.
- CloakBrowser approval workflow or compliance review.
- Full video recording, HAR capture, or unrestricted raw browser-state export.
- Relaxing confirmation rules for destructive or external browser actions.
- Long-term analytics or scheduled report delivery for debug artifacts.

## Risk Classification

Risk flags:

- Audit/security.
- Data model.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Audit/security because browser debug artifacts can contain sensitive session
  data and require retention, access, and redaction controls.

## Work Phases

1. Discovery: confirm artifact, retention, and UI console requirements from
   `SPEC.md`, browser-session docs, and admin retention policy rules.
2. Design: define artifact types, capture triggers, redaction boundaries,
   storage split, and access model.
3. Validation planning: design proof for capture success, capture denial,
   redaction safety, retention expiry, and audit visibility.
4. Implementation: add artifact metadata, storage, retrieval, UI controls, and
   retention behavior for the bounded MVP slice.
5. Verification: prove governed screenshot and debug-artifact handling under
   happy-path and failure-path conditions.
6. Harness update: leave a clean handoff for profile-management and
   CloakBrowser policy stories.

## Stop Conditions

Pause for human confirmation if:

- The story requires storing raw cookies, storage state, or plaintext secrets.
- Artifact retention or deletion needs to weaken tenant or role boundaries.
- The slice needs a new object-storage provider or deployment architecture
  beyond the current local-first baseline.
- Compliance requirements imply a broader governance workflow than the current
  MVP product docs define.
