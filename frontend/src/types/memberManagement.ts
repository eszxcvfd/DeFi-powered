export type MemberRole =
  | "owner"
  | "admin"
  | "compliance"
  | "analyst"
  | "sales_bd"
  | "reviewer"
  | "viewer";

export type MemberState =
  | "active"
  | "disabled"
  | "pending_invite"
  | "revoked"
  | "expired";

export type InvitationState = "pending" | "accepted" | "revoked" | "expired";

export interface MemberView {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: MemberRole;
  state: MemberState;
  created_at: string;
  updated_at: string;
  disabled: boolean;
  last_login_at: string | null;
}

export interface InvitationView {
  id: string;
  email: string;
  role: MemberRole;
  state: InvitationState;
  invited_by_user_id: string;
  invited_by_email: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface MemberListResponse {
  members: MemberView[];
  invitations: InvitationView[];
  total_members: number;
  total_invitations: number;
}

export interface InvitationCreateResponse {
  invitation: InvitationView;
  invite_token: string;
  invite_url: string | null;
  expires_at: string;
}

export interface MemberActionResponse {
  member: MemberView;
  sessions_revoked: number;
}

export interface InvitationActionResponse {
  invitation: InvitationView;
}

export interface InvitationAcceptRequest {
  token: string;
  password: string;
  display_name?: string;
}

export interface InvitationAcceptResponse {
  user_id: string;
  membership_id: string;
  role: MemberRole;
  organization_id: string;
  new_user: boolean;
  expires_in: number;
}
