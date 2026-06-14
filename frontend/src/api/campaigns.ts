import type { CampaignCreatePayload, CampaignDetail, CampaignSummary } from "@/types/campaign";

const headers = { "Content-Type": "application/json" };

export async function listCampaigns(): Promise<CampaignSummary[]> {
  const r = await fetch("/campaigns");
  if (!r.ok) throw new Error("list campaigns failed");
  return r.json();
}

export async function getCampaign(id: string): Promise<CampaignDetail> {
  const r = await fetch(`/campaigns/${id}`);
  if (!r.ok) throw new Error("get campaign failed");
  return r.json();
}

export async function createCampaign(payload: CampaignCreatePayload): Promise<CampaignDetail> {
  const r = await fetch("/campaigns", { method: "POST", headers, body: JSON.stringify(payload) });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(JSON.stringify(err.detail ?? err));
  }
  return r.json();
}