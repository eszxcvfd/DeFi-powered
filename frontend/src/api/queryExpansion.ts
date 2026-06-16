import type { QueryExpansionSet, QueryExpansionVariant } from "@/types/queryExpansion";

export async function generateQueryExpansion(campaignId: string): Promise<QueryExpansionSet> {
  const r = await fetch(`/campaigns/${campaignId}/query-expansions:generate`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<QueryExpansionSet>;
}

export async function getQueryExpansion(campaignId: string): Promise<QueryExpansionSet | null> {
  const r = await fetch(`/campaigns/${campaignId}/query-expansions`);
  if (!r.ok) throw new Error(await r.text());
  if (r.status === 204) return null;
  const text = await r.text();
  if (!text) return null;
  return JSON.parse(text) as QueryExpansionSet;
}

export async function patchQueryExpansion(
  campaignId: string,
  body: { variants?: QueryExpansionVariant[]; approve?: boolean },
): Promise<QueryExpansionSet> {
  const r = await fetch(`/campaigns/${campaignId}/query-expansions`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<QueryExpansionSet>;
}