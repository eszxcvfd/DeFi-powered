# 0014 Member Management Baseline

Date: 2026-06-15

## Status

Accepted

## Context

`US-027` established the first real identity boundary, durable user records,
session lifecycle, RBAC matrix, and tenant isolation, but the product still
has no way to invite a teammate, change their role, disable their access,
or revoke access safely. `SPEC.md` already requires owner/admin member
management, and `docs/product/member-management-and-access-governance.md`
defines the first product contract for the membership surface. The change
touches authentication, authorization, audit, public API shape, and the
existing US-027 behavior, and it must do so without weakening the auth
boundary, breaking tenant isolation, or letting the organization lock itself
out of its own workspace.

## Decision

`US-028` introduces the first member management baseline on top of the
US-027 identity layer:

- The `MembershipState` enum is extended with `pending_invite`, `revoked`,
  and `expired` while keeping the existing `active` and `disabled` values
  the auth and session layers already understand. The session resolver
  treats a non-`active` membership as no longer governable, so a disabled
  or revoked user no longer satisfies the US-027 login check.
- A durable `MemberInvitation` table holds the invitation token, target
  email, organization scope, intended role, expiry, inviter, and
  redemption state. Tokens are stored as a salted SHA-256 hash the same
  way session tokens are stored; the cleartext token is returned to the
  inviter once at creation time and never persisted.
- The new `MemberManagementService` exposes
  `list_organization_members`, `invite_member`, `accept_invitation`,
  `change_member_role`, `disable_member`, `enable_member`,
  `revoke_member_access`, and `revoke_invitation`. Every state-changing
  call records an audit row with a redacted copy of the secret fields
  (invite token, password material) and a `denied` row when governance
  rules block the action.
- The role governance matrix is encoded as a pure function in the domain
  layer: an owner can manage owner-level access; an admin can manage
  non-owner access only. Any demotion, disable, or revoke that would
  leave the organization with zero active owners is rejected as
  `last_owner_protected` and produces a denied audit row.
- A disabled or revoked membership immediately revokes every active
  session for that user on that organization through the existing
  `SessionRepository.revoke_all_for_user` path. A subsequent
  `/auth/login` for that user against the affected organization returns
  the same generic `invalid_credentials` body that US-027 introduced.
- The REST surface follows the contract in
  `docs/product/member-management-and-access-governance.md`:
  `GET /admin/members`, `POST /admin/members/invitations`,
  `POST /admin/members/invitations/{id}/revoke`,
  `POST /auth/invitations/{token}/accept`,
  `PATCH /admin/members/{id}`, and `DELETE /admin/members/{id}`.
  Invitation token reuse, expired tokens, and the last-owner case all
  return distinguishable blocked responses without revealing whether a
  given email already has membership.
- A `Settings -> Members` admin surface is added in the React app so
  owners and admins can list members and invitations, create an invite,
  change a role, disable or re-enable, revoke access, and revoke a
  pending invite. A bounded invite-acceptance modal redeems the
  invitation token into a new or linked user account. Manual handoff
  is explicit; automatic email delivery remains a follow-on story.
- New `AuditAction` and `AuditTargetType` values are added to
  `domain.audit.enums` so the audit log can describe invite, accept,
  revoke, disable, enable, role change, and blocked-governance
  outcomes. Metadata is redacted through the existing US-026 pipeline
  so invite tokens never land in audit metadata.
- A new alembic revision creates the `member_invitations` table with
  organization, email, role, expiry, state, and inviter indexes. The
  `organization_memberships.state` column keeps its default and gains
  the new `pending_invite`, `revoked`, and `expired` values.

## Alternatives Considered

1. Wait for enterprise SSO before adding any member-management story.
   Rejected because `SPEC.md` already requires owner/admin member
   governance and the MVP needs a non-SSO baseline, and because
   `US-027` deliberately left room for an internal identity model
   before SSO federation.
2. Limit the slice to read-only member listing. Rejected because a
   member list without invite, role, or access controls would not
   satisfy `FR-AUTH-003` and would still leave the same hard-gate
   risk for the next story.
3. Send automatic invitation emails in the first slice. Rejected
   because email delivery is a separate dependency and would block a
   bounded governance contract.
4. Reuse the audit log `target_type="user"` for invitation rows.
   Rejected because the governance target for an invite is the
   invitation itself, not a user, and mixing them would weaken the
   audit-log filter UX that `US-026` already established.
5. Allow admins to grant or revoke owner-level access. Rejected for
   this slice because the product doc explicitly carves owner-level
   management to owners, and broadening it would need its own
   decision record.

## Consequences

Positive:

- Owners and admins can govern who has access to a LiveLead
  organization on top of the US-027 auth boundary.
- Disabled or revoked access takes effect immediately for active
  sessions through the existing session revocation path.
- Every successful or blocked governance action is captured in the
  audit log without leaking invite tokens or password material.
- Future SSO, password reset, and notification stories can reuse the
  same `MemberManagementService` and the same audit vocabulary.

Tradeoffs:

- The role governance matrix is intentionally narrow. Custom role
  authoring, bulk provisioning, and cross-organization membership
  transfer are out of scope for this slice.
- Manual invite handoff is a deliberate product choice. Operators
  must copy the invite link or token to the invitee until the
  notification story lands.
- The `MembershipState` enum change is a small breaking change for
  any code that assumed the US-027 two-value enum. The session
  resolver already treats unknown states as non-active, so existing
  callers keep working.

## Follow-Up

- A notification and email-delivery story should reuse
  `MemberManagementService.invite_member` and the audit row, and
  should not duplicate the governance rules.
- An enterprise SSO story should consume
  `MemberManagementService` to provision memberships rather than
  bypassing the governance layer.
- A future retention and deletion story should be able to use the
  invitation `revoked_at` and `expired_at` columns to decide which
  invitation rows to keep.
- A future bulk invite or SCIM story should be able to reuse the
  `pending_invite` lifecycle and the role governance matrix.
