import type { ViewerFeedback } from "@/types/aiFeedback";

export async function putDiscoveryCopilotFeedback(
  responseId: string,
  body: { state: string; reason_code?: string | null; note?: string | null },
): Promise<ViewerFeedback> {
  const r = await fetch(`/discovery-copilot-responses/${responseId}/feedback`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("copilot feedback failed");
  return r.json() as Promise<ViewerFeedback>;
}

export async function putAudienceHypothesisFeedback(
  hypothesisId: string,
  body: { state: string; reason_code?: string | null; note?: string | null },
): Promise<ViewerFeedback> {
  const r = await fetch(`/audience-hypotheses/${hypothesisId}/feedback`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("audience feedback failed");
  return r.json() as Promise<ViewerFeedback>;
}