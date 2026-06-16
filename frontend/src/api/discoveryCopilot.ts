import type { AcceptCopilotResult, DiscoveryCopilotResponse } from "@/types/discoveryCopilot";

export async function askDiscoveryCopilot(
  campaignId: string,
  question: string,
): Promise<DiscoveryCopilotResponse> {
  const r = await fetch(`/campaigns/${campaignId}/discovery-copilot:respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<DiscoveryCopilotResponse>;
}

export async function acceptDiscoveryCopilot(
  campaignId: string,
  responseId: string,
): Promise<AcceptCopilotResult> {
  const r = await fetch(`/campaigns/${campaignId}/discovery-copilot:accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response_id: responseId }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<AcceptCopilotResult>;
}