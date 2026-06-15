# Design

## Domain Model

The story should formalize the first organization-access governance objects:

- `OrganizationMember`: organization-scoped membership with role, status, join
  time, disable or revoke markers, and actor references.
- `MemberInvitation`: pending invite with target email, organization scope,
  intended role, expiry, inviter, and redemption state.
- `MembershipGovernancePolicy`: rules that decide who may invite, disable,
  reactivate, revoke, or change role for whom.
- `MembershipAccessState`: bounded lifecycle such as `pending_invite`, `active`,
  `disabled`, `revoked`, or `expired`.
- `MembershipEvent`: audit-friendly representation of invite, accept, role
  change, disable, enable, revoke, or blocked governance outcomes.

Business rules:

- Every membership and invitation is scoped to one organization.
- Owners may manage owner-level access; admins may manage non-owner access only
  unless a later decision changes that boundary.
- The system must not allow the last active owner to be disabled, revoked, or
  demoted.
- Invitation redemption must bind to the invited email address and the role set
  by the inviter; acceptance must not become a privilege-escalation path.
- Disabled or revoked members must lose authenticated access to that
  organization, including existing active sessions where applicable.
- Revoked or expired invitations must never be redeemable.

## Application Flow

- `ListOrganizationMembers` returns current memberships and pending invitations
  for the authenticated organization.
- `InviteOrganizationMember` validates inviter authority, creates one pending
  invitation, records expiry, and returns a safe invitation handoff artifact.
- `AcceptOrganizationInvitation` validates the token, invited email, and
  invitation state, then activates the membership and creates or links the user
  account as needed.
- `ChangeOrganizationMemberRole` enforces governance rules and last-owner
  protection before committing a role change.
- `DisableOrganizationMember`, `EnableOrganizationMember`, and
  `RevokeOrganizationMemberAccess` update membership state and invalidate active
  organization sessions where necessary.
- `RevokeOrganizationInvitation` marks a pending invite unusable without
  changing existing active memberships.

## Interface Contract

Backend contract should minimally support:

- `GET /admin/members` for list and status reads.
- `POST /admin/members/invitations` for invite creation.
- `POST /auth/invitations/{token}/accept` or equivalent invite-acceptance path.
- `PATCH /admin/members/{id}` or equivalent for bounded role/status updates.
- `DELETE /admin/members/{id}` or equivalent revoke-access action.
- `POST /admin/members/invitations/{id}/revoke` or equivalent pending-invite
  cancellation.

Expected payload concerns:

- Responses should expose membership status, role, invite expiry, inviter or
  actor summary, and joined timestamps without leaking raw secret material.
- Invite tokens or links must be treated as secrets in logs and audit metadata;
  operators may receive a safe copyable handoff value without raw persistence in
  read APIs after creation.
- Blocked governance responses should distinguish authorization failure,
  last-owner protection, invalid state, and missing membership or invitation.

## Data Model

- Add durable membership and invitation tables or equivalent structures with
  organization scope, normalized role, lifecycle status, expiry, inviter,
  redeemer, and revocation metadata.
- Keep membership state separate from session state so session invalidation can
  be enforced without losing governance history.
- Index by organization, email, active status, and invitation token lookup as
  needed for repeatable reads and acceptance flow.
- Reuse the audit system from `US-026` and the authenticated actor context from
  `US-027` rather than inventing a parallel governance-history path.
- Preserve room for later email-delivery status, SCIM linkage, or external IdP
  references without redefining the baseline membership model.

## UI / Platform Impact

- Add a first Settings -> Members admin surface in the React app.
- Add an invite flow that is explicit when delivery is manual rather than email-
  driven.
- Show clear blocked states for “cannot remove last owner”, “cannot manage owner
  role”, “invite expired”, and “access revoked”.
- Keep the first UI narrow and governed: no bulk tables with spreadsheet-style
  editing, no SSO-provider management, and no billing-adjacent admin settings.

## Observability

- Record audit entries for invite created, invite accepted, invite revoked,
  member disabled, member enabled, role changed, access revoked, and blocked
  governance attempts.
- Emit structured diagnostics when session invalidation, last-owner protection,
  or invite redemption fails.
- Preserve correlation between membership events, authenticated actor context,
  and session revocation outcomes for later support and compliance review.

## Alternatives Considered

1. Wait for enterprise SSO before adding any member-management story. Rejected
   because the spec already requires owner/admin member governance and the MVP
   needs a non-SSO baseline.
2. Limit the slice to read-only member listing. Rejected because a member list
   without invite, role, or access controls would not satisfy `FR-AUTH-003`.
3. Send automatic invitation emails in the first slice. Rejected because email
   delivery is a separate dependency and should not block a bounded governance
   contract.
