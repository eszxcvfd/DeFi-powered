# Member Management And Access Governance

Source: `SPEC.md` sections 2.3, 5.1, 6.2, 8.1, 10.3, 10.4, 12, and 14.3.

## Product Goal

Owners and admins need a governed way to control who can access one LiveLead
organization and what role each person holds after the auth boundary from
`docs/product/identity-and-access.md` exists. The MVP must let the right
operators invite teammates, activate or deactivate access, adjust roles, and
revoke access without breaking tenant isolation, weakening auditability, or
locking an organization out of its own workspace.

## MVP Scope

This product slice covers:

- Listing organization members and pending invitations in one governed admin
  surface.
- Creating a member invitation for one email address and one target role.
- Accepting an invitation through a bounded invite-acceptance flow that creates
  or links a user to the organization membership.
- Changing a member's baseline role within the current organization according to
  role-governance rules.
- Disabling, re-enabling, or revoking organization access for a member.
- Revoking pending invitations before they are accepted.
- Ending or invalidating active sessions when access is revoked or disabled.
- Audit capture for invitation creation, acceptance, revoke, disable, role
  change, and blocked governance attempts.

This product slice does not yet cover:

- Automatic email delivery for invitations or reminder cadences.
- Bulk invite/import flows.
- SAML, OIDC, SCIM, or directory synchronization.
- Fine-grained permission editing below the baseline role set.
- Cross-organization membership switching UX beyond the currently active
  organization context.

## Contract Rules

- Member-management actions are organization-scoped governance actions and must
  be enforced in the backend.
- Owner/Admin access is not symmetric by default: owners may manage owner-level
  memberships, while admins must not grant, remove, or disable owner access
  unless a later decision explicitly broadens that rule.
- The system must prevent removal or disablement of the last active owner in an
  organization.
- Disabled or revoked memberships must stop receiving authenticated access, and
  any active sessions for that organization should no longer remain valid.
- Invitations must be single-purpose and bounded to one organization, one email
  address, and one intended role.
- Invitation acceptance must not let the accepting user escalate beyond the role
  attached to the invitation.
- The product must show clear state for `pending_invite`, `active`,
  `disabled`, `revoked`, or `expired` membership-related records.
- Email delivery is optional in a later story; this baseline must still support
  safe manual handoff of an invite link or invite token.
- All invite, role, disable, enable, revoke, and blocked-governance actions
  must be auditable with secret-safe metadata.

## API Surface

- `GET /admin/members`: list current members and invitation state for the active
  organization.
- `POST /admin/members/invitations`: create a pending invitation with target
  email and role.
- `POST /auth/invitations/{token}/accept` or equivalent accept flow: redeem an
  invitation into an active organization membership.
- `PATCH /admin/members/{id}` or equivalent role/status update route: change
  role, disable, or re-enable a member within the bounded governance rules.
- `DELETE /admin/members/{id}` or equivalent revoke-access action: remove access
  from the organization and invalidate active sessions.
- `POST /admin/members/invitations/{id}/revoke` or equivalent action: cancel a
  pending invitation safely.

## Admin UI Surface

The first membership-governance surface should stay clear and operator-oriented:

- Settings -> Members list with role, state, joined time, invited time, and
  recent governance actions where helpful.
- Invite modal or page for email plus role selection, with explicit note when
  delivery is manual rather than email-based.
- Inline or detail actions for role change, disable, re-enable, revoke access,
  and revoke invite.
- Clear blocked-action messaging when a user tries to remove the last owner or
  exceed their governance role.
- No organization-billing, SSO-provider, or SCIM admin controls in this slice.

## Validation Implications

- Unit proof should cover invitation lifecycle rules, role-governance rules,
  last-owner protection, and session invalidation decisions.
- Integration proof should cover invite creation, acceptance, role change,
  disable or revoke behavior, protected-route blocking after access loss, and
  tenant-scoped member reads.
- E2E proof should cover an owner/admin inviting a user, seeing the invite in
  the admin surface, accepting the invite through the UI flow, and later
  disabling or changing the member role safely.
- Logs and audit proof should confirm every successful or blocked governance
  action creates an audit record without exposing raw invite secrets.
- Platform proof should keep auth-aware membership management wired into the
  Harness matrix before notification, SSO, or directory-sync stories build on
  it.
