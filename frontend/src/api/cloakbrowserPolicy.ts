import type { CloakBrowserPolicyView } from "@/types/cloakbrowserPolicy";

const jsonHeaders = { "Content-Type": "application/json" };

function adminHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "admin" };
}

function complianceHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "compliance" };
}

export async function getCloakBrowserPolicy(sourceId: string): Promise<CloakBrowserPolicyView> {
  const r = await fetch(`/admin/cloakbrowser-policy/sources/${sourceId}`, { headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function requestCloakBrowser(
  sourceId: string,
  payload: { purpose_rationale: string; pinned_version?: string }
): Promise<CloakBrowserPolicyView> {
  const r = await fetch(`/admin/cloakbrowser-policy/sources/${sourceId}/request`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function approveOwnerAdmin(sourceId: string): Promise<CloakBrowserPolicyView> {
  const r = await fetch(`/admin/cloakbrowser-policy/sources/${sourceId}/approve-owner-admin`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function approveCompliance(sourceId: string): Promise<CloakBrowserPolicyView> {
  const r = await fetch(`/admin/cloakbrowser-policy/sources/${sourceId}/approve-compliance`, {
    method: "POST",
    headers: complianceHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function revokeCloakBrowser(
  sourceId: string,
  reason: string
): Promise<CloakBrowserPolicyView> {
  const r = await fetch(`/admin/cloakbrowser-policy/sources/${sourceId}/revoke`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}