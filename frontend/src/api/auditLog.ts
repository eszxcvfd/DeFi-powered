import type { AuditEntry, AuditFilterOptions, AuditList } from "@/types/auditLog";

const jsonHeaders = { "Content-Type": "application/json" };

function adminHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "admin" };
}

function buildQuery(params: Record<string, string | number | null | undefined>): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export async function listAuditEntries(params: {
  actor_id?: string;
  actor_type?: string;
  action?: string;
  action_family?: string;
  target_type?: string;
  target_id?: string;
  outcome?: string;
  request_id?: string;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<AuditList> {
  const r = await fetch(`/admin/audit-logs${buildQuery(params)}`, {
    headers: adminHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getAuditEntry(entryId: string): Promise<AuditEntry> {
  const r = await fetch(`/admin/audit-logs/${entryId}`, { headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getAuditFilterOptions(): Promise<AuditFilterOptions> {
  const r = await fetch("/admin/audit-logs/filters", { headers: adminHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
