# Exec Plan

## Goal

Define the first admin audit-log slice so LiveLead can record and inspect
tenant-scoped sensitive actions with secret-safe metadata, role-gated access,
and a stable governance contract before retention, deletion, and broader
hardening work arrives.

## Scope

In scope:

- Normalized audit-entry capture for representative implemented workflows such as
  login outcome, source-policy decisions, discovery control, content review,
  confirmation-gated browser actions, and lead or browser-governance changes.
- Read-only admin audit list/detail surfaces and API contracts.
- Secret-safe redaction rules and append-only application behavior.
- Tenant-scoped query filters for actor, action, target, result, and time range.
- Correlation or request context fields needed to reconstruct multi-step flows.

Out of scope:

- Retention-policy configuration UI or scheduled cleanup jobs.
- Data deletion, anonymization, or privacy export workflows.
- Connector-health dashboards and alerting.
- Broad member invitation, role editing, or SSO-provider management.
- External audit export, SIEM sync, or compliance case-management workflows.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Auth and audit/security because the story records login outcomes and governance
  events while introducing a new admin-facing read surface.

## Work Phases

1. Discovery: confirm audit, admin UI, and security requirements from `SPEC.md`,
   current product docs, and existing implemented workflow boundaries.
2. Design: define audit event shape, actor or target model, redaction rules, and
   append-only behavior.
3. Validation planning: design proof for representative event capture, tenant
   isolation, role-gated reads, and secret-safe metadata.
4. Implementation: add the bounded backend audit write/read path and admin audit
   surface.
5. Verification: prove representative workflows create readable audit entries
   without weakening security or tenant boundaries.
6. Harness update: leave a clean handoff for retention-policy, deletion, and
   connector-health stories.

## Stop Conditions

Pause for human confirmation if:

- The story requires exposing raw secrets, cookies, or unredacted payloads to
  make the audit surface useful.
- Audit read access needs to widen beyond owner/admin governance roles.
- The slice depends on a new external log store, SIEM contract, or cross-tenant
  aggregation model not yet defined in product docs.
- Retention or privacy requirements force deletion behavior into this story's
  scope.
