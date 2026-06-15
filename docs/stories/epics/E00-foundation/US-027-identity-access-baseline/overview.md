# Overview

## Current Behavior

LiveLead already stores `organization_id` on most product records and several
routes make lightweight role checks, but the repo still uses development
headers (`X-Organization-Id` and `X-Actor-Role`) as the HTTP auth boundary.
There is no real login flow, no durable user or session contract, no stable
role matrix across the implemented surfaces, and no authenticated replacement
for the seeded dev tenant context.

## Target Behavior

This story should establish the first real identity and access slice for
LiveLead:

- Replace header-based development auth with a bounded authenticated session
  flow for human users.
- Introduce a durable user, organization-membership, and baseline role model
  for Owner, Admin, Analyst, Sales/BD, Reviewer, and Viewer.
- Enforce backend RBAC and tenant isolation across the already implemented API
  and UI surfaces.
- Add minimal session-aware UI behavior for sign-in, sign-out, expired-session,
  and unauthorized states.
- Preserve audit-safe records for login success, login failure, logout, and
  representative authorization denials.

The story should create a safe baseline for later member management, password
recovery, notifications, or SSO work without leaving the repo dependent on
dev-only headers.

## Affected Users

- Owner/Admin users who need governed access to connector, profile, and audit
  surfaces.
- Analysts, Sales/BD users, Reviewers, and Viewers who need the correct role
  and tenant context when using existing product flows.
- Future implementation agents extending member management, notifications, or
  SSO on top of a stable auth boundary.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/identity-and-access.md`
- `docs/product/audit-log-and-governance.md`

## Non-Goals

- Full member invitation, disablement, or role-management UX.
- SAML, OIDC, or enterprise SSO provider rollout.
- MFA, password-reset, or email-verification workflows.
- Fine-grained permission editing beyond the first baseline role matrix.
- Privacy deletion or retention-policy behavior.
