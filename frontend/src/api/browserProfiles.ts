const adminHeaders = (): HeadersInit => ({
  "Content-Type": "application/json",
  "X-Actor-Role": "admin",
});

export type BrowserProfileView = {
  id: string;
  name: string;
  lifecycle_state: string;
  effective_state: string;
  launch_eligible: boolean;
  launch_blocked_reasons: string[];
  consent_status: string;
  state_material_present: boolean;
  raw_state_exposed: boolean;
  expires_at: string | null;
  last_used_at: string | null;
};

export async function listBrowserProfiles(): Promise<BrowserProfileView[]> {
  const r = await fetch("/admin/browser-profiles", { headers: adminHeaders() });
  if (!r.ok) throw new Error("list browser profiles failed");
  return r.json();
}

export async function createBrowserProfile(name: string, ttlDays = 30): Promise<BrowserProfileView> {
  const r = await fetch("/admin/browser-profiles", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ name, ttl_days: ttlDays }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function lockBrowserProfile(id: string): Promise<BrowserProfileView> {
  const r = await fetch(`/admin/browser-profiles/${id}/lock`, { method: "POST", headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function renewBrowserProfile(id: string): Promise<BrowserProfileView> {
  const r = await fetch(`/admin/browser-profiles/${id}/renew`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ ttl_days: 30 }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function expireBrowserProfile(id: string): Promise<BrowserProfileView> {
  const r = await fetch(`/admin/browser-profiles/${id}/expire`, { method: "POST", headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteBrowserProfile(id: string): Promise<BrowserProfileView> {
  const r = await fetch(`/admin/browser-profiles/${id}`, { method: "DELETE", headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}