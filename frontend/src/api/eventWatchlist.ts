import type { EventWatchState } from "@/types/event";

export type WatchlistHistoryEntry = {
  id: string;
  action: string;
  actor_id: string;
  actor_role: string;
  from_reminder_at: string | null;
  to_reminder_at: string | null;
  note: string;
  created_at: string;
};

export type WatchlistEntryResponse = {
  entry_id: string;
  watch: EventWatchState;
  history: WatchlistHistoryEntry[];
};

export type WatchedEventRow = {
  entry_id: string;
  event_id: string;
  campaign_id: string;
  campaign_name: string;
  canonical_title: string;
  source_url: string;
  observed_at: string;
  region: string;
  starts_at: string | null;
  reminder_at: string | null;
  reminder_status: "not_watched" | "scheduled" | "overdue";
  reminder_note: string;
  last_action_at: string | null;
};

export type WatchedEventListResponse = {
  items: WatchedEventRow[];
  total: number;
};

export type UpsertWatchlistRequest = {
  reminder_at: string | null;
  reminder_note?: string;
};

async function unwrapError(r: Response, fallback: string): Promise<Error> {
  const body = (await r.json().catch(() => ({}))) as { detail?: string };
  return new Error(body.detail ?? fallback);
}

export async function upsertEventWatchlist(
  eventId: string,
  body: UpsertWatchlistRequest,
): Promise<WatchlistEntryResponse> {
  const r = await fetch(`/events/${eventId}/watchlist`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw await unwrapError(r, "watchlist update failed");
  return r.json();
}

export async function removeEventWatchlist(
  eventId: string,
): Promise<WatchlistEntryResponse> {
  const r = await fetch(`/events/${eventId}/watchlist`, { method: "DELETE" });
  if (!r.ok) throw await unwrapError(r, "watchlist remove failed");
  return r.json();
}

export async function listWatchedEvents(
  hasReminder?: boolean,
): Promise<WatchedEventListResponse> {
  const sp = new URLSearchParams();
  if (hasReminder !== undefined) sp.set("has_reminder", String(hasReminder));
  const qs = sp.toString();
  const r = await fetch(`/watchlist/events${qs ? `?${qs}` : ""}`);
  if (!r.ok) throw await unwrapError(r, "watched events list failed");
  return r.json();
}
