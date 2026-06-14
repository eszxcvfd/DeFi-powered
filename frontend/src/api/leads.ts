import type { LeadDetail, LeadSummary } from "@/types/lead";

export type ListLeadsParams = {
  owner?: string;
  campaign_id?: string;
  discovery_source?: string;
};

export async function listLeads(params: ListLeadsParams = {}): Promise<LeadSummary[]> {
  const sp = new URLSearchParams();
  if (params.owner) sp.set("owner", params.owner);
  if (params.campaign_id) sp.set("campaign_id", params.campaign_id);
  if (params.discovery_source) sp.set("discovery_source", params.discovery_source);
  const q = sp.toString();
  const r = await fetch(`/leads${q ? `?${q}` : ""}`);
  if (!r.ok) throw new Error("list leads failed");
  return r.json();
}

export async function getLead(id: string): Promise<LeadDetail> {
  const r = await fetch(`/leads/${id}`);
  if (!r.ok) throw new Error("get lead failed");
  return r.json();
}

export async function createLead(body: Record<string, unknown>): Promise<LeadDetail> {
  const r = await fetch("/leads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "create lead failed");
  }
  return r.json();
}

export async function patchLead(id: string, body: Record<string, unknown>): Promise<LeadDetail> {
  const r = await fetch(`/leads/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("patch lead failed");
  return r.json();
}