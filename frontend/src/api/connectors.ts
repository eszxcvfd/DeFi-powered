import type { ConnectorView, RunnableSource } from "@/types/connector";

const jsonHeaders = { "Content-Type": "application/json" };

function adminHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "admin" };
}

export async function listConnectors(): Promise<ConnectorView[]> {
  const r = await fetch("/admin/connectors", { headers: adminHeaders() });
  if (!r.ok) throw new Error("list connectors failed");
  return r.json();
}

export async function createConnector(payload: Record<string, unknown>): Promise<ConnectorView> {
  const r = await fetch("/admin/connectors", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listRunnableSources(): Promise<RunnableSource[]> {
  const r = await fetch("/campaigns/runnable-sources");
  if (!r.ok) throw new Error("runnable sources failed");
  return r.json();
}

export async function setCampaignSources(campaignId: string, sourceIds: string[]): Promise<RunnableSource[]> {
  const r = await fetch(`/campaigns/${campaignId}/sources`, {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify({ source_ids: sourceIds }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}