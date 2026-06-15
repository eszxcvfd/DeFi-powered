import type {
  InvitationAcceptRequest,
  InvitationAcceptResponse,
  InvitationActionResponse,
  InvitationCreateResponse,
  MemberActionResponse,
  MemberListResponse,
} from "@/types/memberManagement";

async function parseError(r: Response): Promise<never> {
  const text = await r.text();
  try {
    const json = JSON.parse(text);
    if (json && typeof json === "object" && "detail" in json) {
      const detail = (json as { detail: unknown }).detail;
      if (detail && typeof detail === "object" && "message" in (detail as Record<string, unknown>)) {
        throw new Error((detail as { message: string }).message);
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  } catch (e) {
    if (e instanceof Error) throw e;
  }
  throw new Error(text || "member management request failed");
}

export async function listMembers(): Promise<MemberListResponse> {
  const r = await fetch("/admin/members", { credentials: "same-origin" });
  if (!r.ok) await parseError(r);
  return (await r.json()) as MemberListResponse;
}

export async function createInvitation(input: {
  email: string;
  role: string;
}): Promise<InvitationCreateResponse> {
  const r = await fetch("/admin/members/invitations", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as InvitationCreateResponse;
}

export async function revokeInvitation(
  invitationId: string,
  reason?: string,
): Promise<InvitationActionResponse> {
  const r = await fetch(`/admin/members/invitations/${invitationId}/revoke`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason ?? null }),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as InvitationActionResponse;
}

export async function changeMemberRole(
  membershipId: string,
  role: string,
): Promise<MemberActionResponse> {
  const r = await fetch(`/admin/members/${membershipId}`, {
    method: "PATCH",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as MemberActionResponse;
}

export async function disableMember(membershipId: string): Promise<MemberActionResponse> {
  const r = await fetch(`/admin/members/${membershipId}/disable`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as MemberActionResponse;
}

export async function enableMember(membershipId: string): Promise<MemberActionResponse> {
  const r = await fetch(`/admin/members/${membershipId}/enable`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as MemberActionResponse;
}

export async function revokeMemberAccess(
  membershipId: string,
): Promise<MemberActionResponse> {
  const r = await fetch(`/admin/members/${membershipId}`, {
    method: "DELETE",
    credentials: "same-origin",
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as MemberActionResponse;
}

export async function acceptInvitation(
  input: InvitationAcceptRequest,
): Promise<InvitationAcceptResponse> {
  const r = await fetch("/auth/invitations/accept", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as InvitationAcceptResponse;
}
