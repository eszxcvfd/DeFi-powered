import type {
  ScoringSuggestionApproveResponse,
  ScoringSuggestionSet,
} from "@/types/scoringSuggestions";
const headers = { "Content-Type": "application/json" };

export async function listScoringSuggestions(campaignId: string): Promise<ScoringSuggestionSet[]> {
  const r = await fetch(`/campaigns/${campaignId}/scoring-suggestions`);
  if (!r.ok) throw new Error("list scoring suggestions failed");
  return r.json();
}

export async function generateScoringSuggestions(campaignId: string): Promise<ScoringSuggestionSet> {
  const r = await fetch(`/campaigns/${campaignId}/scoring-suggestions:generate`, { method: "POST" });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(JSON.stringify(err.detail ?? err));
  }
  return r.json();
}

export async function approveScoringSuggestion(
  campaignId: string,
  suggestionId: string
): Promise<ScoringSuggestionApproveResponse> {
  const r = await fetch(
    `/campaigns/${campaignId}/scoring-suggestions/${suggestionId}:approve`,
    { method: "POST", headers }
  );
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(JSON.stringify(err.detail ?? err));
  }
  return r.json();
}

export async function rejectScoringSuggestion(
  campaignId: string,
  suggestionId: string,
  reviewNote?: string
): Promise<ScoringSuggestionSet> {
  const r = await fetch(
    `/campaigns/${campaignId}/scoring-suggestions/${suggestionId}:reject`,
    { method: "POST", headers, body: JSON.stringify({ review_note: reviewNote ?? null }) }
  );
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(JSON.stringify(err.detail ?? err));
  }
  return r.json();
}