import type { CampaignEventListItem, EventDetail } from "@/types/event";

export type ListEventsParams = {
  q?: string;
  discovery_job_id?: string;
  source_id?: string;
  include_score?: boolean;
  limit?: number;
  watched?: boolean;
};

function queryString(params: ListEventsParams): string {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.discovery_job_id) sp.set("discovery_job_id", params.discovery_job_id);
  if (params.source_id) sp.set("source_id", params.source_id);
  if (params.include_score === false) sp.set("include_score", "false");
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.watched !== undefined) sp.set("watched", String(params.watched));
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function listOrganizationEvents(
  params: Pick<ListEventsParams, "q" | "limit" | "include_score" | "watched"> = {},
): Promise<CampaignEventListItem[]> {
  const r = await fetch(`/events${queryString(params)}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "list events failed");
  }
  return r.json();
}

export async function listCampaignEvents(
  campaignId: string,
  params: ListEventsParams = {},
): Promise<CampaignEventListItem[]> {
  const r = await fetch(`/campaigns/${campaignId}/events${queryString(params)}`);
  if (!r.ok) throw new Error("list campaign events failed");
  return r.json();
}

export type BrowserLaunchSourceOption = {
  source_id: string;
  name: string;
  domain: string;
  automation_engine: string;
  engine: string;
  runnable: boolean;
  denied_reasons: string[];
};

export async function listEventBrowserLaunchSources(
  eventId: string,
): Promise<BrowserLaunchSourceOption[]> {
  const r = await fetch(`/events/${eventId}/browser-launch-sources`);
  if (!r.ok) throw new Error("browser launch sources failed");
  return r.json();
}

export async function getEvent(eventId: string): Promise<EventDetail> {
  const r = await fetch(`/events/${eventId}`);
  if (!r.ok) throw new Error("get event failed");
  return r.json();
}

export async function refreshAudience(eventId: string): Promise<EventDetail> {
  const r = await fetch(`/events/${eventId}/audience/refresh`, { method: "POST" });
  if (!r.ok) throw new Error("audience refresh failed");
  return r.json();
}

export async function rescoreEvent(eventId: string): Promise<EventDetail> {
  const r = await fetch(`/events/${eventId}/rescore`, { method: "POST" });
  if (!r.ok) throw new Error("rescore failed");
  return r.json();
}

export async function createEngagementPlan(eventId: string): Promise<EventDetail> {
  const r = await fetch(`/events/${eventId}/engagement-plans`, { method: "POST" });
  if (!r.ok) throw new Error("engagement plan failed");
  return r.json();
}

export async function patchEngagementTask(
  eventId: string,
  taskId: string,
  body: { status?: string; assignee?: string; notes?: string },
): Promise<EventDetail> {
  const r = await fetch(`/events/${eventId}/engagement-tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("task update failed");
  return r.json();
}