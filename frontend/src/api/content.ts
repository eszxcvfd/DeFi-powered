export type ContentContext = {
  event_title: string;
  event_description: string;
  campaign_focus: string;
  score_summary: string;
  audience_summary: string;
  plan_task_count: number;
  notes: string[];
};

export type ContentReviewDecision = {
  id: string;
  action: string;
  from_status: string;
  to_status: string;
  actor: string;
  note: string;
  body_revision: number;
  created_at: string;
};

export type ContentHandoffRecord = {
  id: string;
  action: string;
  actor: string;
  export_format: string;
  body_revision: number;
  created_at: string;
};

export type ContentDraft = {
  id: string;
  event_id: string;
  variant_index: number;
  review_status: string;
  body_revision: number;
  reviewer_assignee: string;
  ready_for_use: boolean;
  usage_status: string;
  handoff_available: boolean;
  export_formats: string[];
  latest_handoff_at: string | null;
  latest_handoff_actor: string;
  settings: {
    content_type: string;
    platform: string;
    language: string;
    tone: string;
    length: string;
    market_context: string;
    cta: string;
    variant_count: number;
  };
  body_text: string;
  risk_flags: { code: string; message: string; severity: string }[];
  provider: string;
  model: string;
  prompt_template_version: string;
  last_editor: string;
  review_history?: ContentReviewDecision[];
  handoff_history?: ContentHandoffRecord[];
};

export type GenerateContentBody = {
  event_id: string;
  settings: {
    content_type: string;
    platform: string;
    language: string;
    tone: string;
    length: string;
    cta: string;
    variant_count: number;
  };
};

const reviewHeaders = { "X-Actor-Role": "reviewer" };

export async function fetchContentContext(eventId: string): Promise<ContentContext> {
  const r = await fetch(`/events/${eventId}/content/context`);
  if (!r.ok) throw new Error("content context failed");
  return r.json();
}

export async function generateContent(
  body: GenerateContentBody,
): Promise<{ context: ContentContext; drafts: ContentDraft[] }> {
  const r = await fetch("/content/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("content generate failed");
  return r.json();
}

export async function listContentDrafts(eventId: string): Promise<ContentDraft[]> {
  const r = await fetch(`/events/${eventId}/content/drafts`);
  if (!r.ok) throw new Error("list drafts failed");
  return r.json();
}

export async function patchContentDraft(eventId: string, draftId: string, body_text: string): Promise<ContentDraft> {
  const r = await fetch(`/events/${eventId}/content/drafts/${draftId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body_text, editor: "analyst" }),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    const msg = typeof detail?.detail === "string" ? detail.detail : `patch draft failed (${r.status})`;
    throw new Error(msg);
  }
  return r.json();
}

export async function submitForReview(eventId: string, draftId: string): Promise<ContentDraft> {
  const r = await fetch(`/events/${eventId}/content/drafts/${draftId}/submit-for-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignee: "" }),
  });
  if (!r.ok) throw new Error("submit for review failed");
  return r.json();
}

export async function approveContent(eventId: string, draftId: string, note = ""): Promise<ContentDraft> {
  const r = await fetch(`/content/${draftId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...reviewHeaders },
    body: JSON.stringify({ event_id: eventId, note, actor: "reviewer" }),
  });
  if (!r.ok) throw new Error("approve failed");
  return r.json();
}

export async function recordContentCopy(eventId: string, draftId: string): Promise<ContentDraft> {
  const r = await fetch(`/content/${draftId}/record-copy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, actor: "analyst" }),
  });
  if (!r.ok) throw new Error("record copy failed");
  return r.json();
}

export function exportContentUrl(eventId: string, draftId: string, format: "markdown" | "csv"): string {
  const q = new URLSearchParams({ event_id: eventId, format, actor: "analyst" });
  return `/content/${draftId}/export?${q.toString()}`;
}

export async function markContentUsed(eventId: string, draftId: string): Promise<ContentDraft> {
  const r = await fetch(`/content/${draftId}/mark-used`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, actor: "analyst" }),
  });
  if (!r.ok) throw new Error("mark used failed");
  return r.json();
}

export async function rejectContent(eventId: string, draftId: string, note: string): Promise<ContentDraft> {
  const r = await fetch(`/content/${draftId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...reviewHeaders },
    body: JSON.stringify({ event_id: eventId, note, actor: "reviewer" }),
  });
  if (!r.ok) throw new Error("reject failed");
  return r.json();
}