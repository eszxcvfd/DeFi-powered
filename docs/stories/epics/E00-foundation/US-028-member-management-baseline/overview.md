# Overview

## Current Behavior

LiveLead now has a planned identity-and-access baseline in `US-027`, but the
product still does not define how an organization adds teammates, changes their
roles, disables access, or revokes membership safely. `SPEC.md` already
requires owner/admin member management, yet there is no product contract or
story packet for invitations, membership lifecycle, or last-owner guardrails.

## Target Behavior

This story should establish the first member-management slice for LiveLead:

- List current members and pending invitations for one organization.
- Let owner/admin users create invitations for teammates with one bounded role.
- Let invitees accept that invitation into an organization membership.
- Allow governed role change, disable, re-enable, and revoke-access actions.
- Invalidate access safely when membership is disabled or revoked.
- Preserve audit-safe evidence for successful and blocked membership-governance
  actions.

This story should make organization access governable after `US-027` without
pulling in enterprise SSO, bulk invite operations, or notification delivery.

## Affected Users

- Owners who must preserve access control and avoid lockout of the organization.
- Admins who manage day-to-day teammate onboarding and role assignment within
  bounded governance rules.
- Analysts, Sales/BD users, Reviewers, and Viewers whose access may be invited,
  changed, disabled, or revoked.
- Future implementation agents extending notifications, SSO, or directory-sync
  flows on top of a stable membership contract.

## Affected Product Docs

- `docs/product/identity-and-access.md`
- `docs/product/member-management-and-access-governance.md`
- `docs/product/audit-log-and-governance.md`

## Non-Goals

- Automatic invitation emails or reminder delivery.
- Bulk invite/import or CSV user provisioning.
- Enterprise SSO, SCIM, or directory synchronization.
- Fine-grained permission editing below the baseline role set.
- Billing, subscription, or organization ownership transfer workflows.
