# Exec Plan

## Goal

Define and implement the first real identity boundary so LiveLead can stop
depending on header-based development auth and instead use authenticated
sessions, backend-enforced RBAC, and tenant isolation across the already
implemented product surface.

## Scope

In scope:

- Email-and-password login baseline.
- Durable user, organization-membership, and authenticated-session records.
- Backend authorization matrix for the current Owner, Admin, Analyst, Sales/BD,
  Reviewer, and Viewer roles.
- Tenant-isolated authenticated context used by existing implemented routes.
- Minimal sign-in, sign-out, expired-session, and unauthorized UI handling.
- Audit-safe auth and authorization event capture.
- Verification fixtures that prove real auth can replace current header-driven
  development access.

Out of scope:

- Member invitation or role-management UI.
- Enterprise SSO, SAML, OIDC, SCIM, or directory sync.
- MFA, password reset, or email verification.
- Fine-grained permissions beyond the baseline role matrix.
- Privacy deletion, retention-policy editing, or notification delivery.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.

Hard gates:

- Auth.
- Authorization.
- Audit/security.

## Work Phases

1. Discovery: confirm identity, RBAC, tenant, audit, and session requirements
   from `SPEC.md`, `docs/ARCHITECTURE.md`, and the current header-based auth
   scaffolding.
2. Design: define the first user, membership, role-policy, and session model,
   including how existing admin/reviewer/sales workflows map onto it.
3. Validation planning: design proof for login success and failure, protected
   route access, cross-tenant denial, session expiry, and audit capture.
4. Implementation: add the bounded backend auth flow, route protection,
   frontend session bootstrap, and local verification fixtures.
5. Verification: prove implemented flows work without the dev header contract
   as the normal path.
6. Harness update: keep product docs current, update durable story proof, and
   record any unresolved auth direction as a decision or backlog item.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The team wants enterprise SSO, MFA, or a stateless token model as a mandatory
  requirement for this first baseline instead of a bounded session slice.
- Existing browser-governance flows require a new permanent product role or
  cross-tenant approval model beyond the current role list in `SPEC.md`.
