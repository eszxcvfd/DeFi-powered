# Exec Plan

## Goal

Define and implement the first member-management baseline so LiveLead
organizations can invite teammates, govern roles, and revoke access safely on
top of the authenticated session boundary introduced by `US-027`.

## Scope

In scope:

- Membership listing for the authenticated organization.
- Invitation creation, acceptance, and revoke flow.
- Role change, disable, re-enable, and revoke-access actions.
- Last-owner protection and owner/admin governance boundaries.
- Session invalidation after access disablement or revocation.
- Minimal admin UI for membership governance.
- Audit-safe membership-governance evidence.

Out of scope:

- Automatic invitation email delivery or reminder cadences.
- Bulk provisioning or CSV import.
- Enterprise SSO, SCIM, or directory synchronization.
- Fine-grained permissions below the baseline role set.
- Billing, subscription, or ownership-transfer workflows.

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

1. Discovery: confirm member-management requirements from `SPEC.md`, the
   identity/access contract, and the current admin-governance surface.
2. Design: define invitation, membership lifecycle, last-owner protection, and
   role-governance rules.
3. Validation planning: design proof for invite creation and acceptance, role
   changes, blocked owner-protection flows, revoked-access session invalidation,
   and audit capture.
4. Implementation: add the bounded backend governance flow, admin members UI,
   and acceptance path needed for a usable baseline.
5. Verification: prove invited users can join safely, governance actions are
   role-bounded, and revoked or disabled access no longer works.
6. Harness update: keep product docs current, update durable story proof, and
   capture any follow-on notification or SSO friction explicitly.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The team wants invitation delivery, MFA, or SSO as a mandatory part of this
  baseline rather than a follow-on story.
- The role matrix needs new product roles beyond Owner, Admin, Analyst,
  Sales/BD, Reviewer, and Viewer to support member governance safely.
