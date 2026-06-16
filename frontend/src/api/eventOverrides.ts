import type {
  EventChangeHistoryEntry,
  EventFieldProvenance,
  EventOverrideEntry,
} from "@/types/event";

export type EventOverridesResponse = {
  event_id: string;
  fields_allowed: string[];
  overrides: EventOverrideEntry[];
  provenance: EventFieldProvenance[];
};

export type EventChangeHistoryResponse = {
  event_id: string;
  history: EventChangeHistoryEntry[];
  total: number;
};

export type EventPatchResponse = {
  event_id: string;
  applied_fields: string[];
  skipped_fields: { field: string; reason: string }[];
  overrides: EventOverrideEntry[];
  history: EventChangeHistoryEntry[];
};

export type EventOverrideClearResponse = {
  event_id: string;
  field: string;
  restored_value: string | number | null;
  history: EventChangeHistoryEntry[];
};

async function unwrapError(r: Response, fallback: string): Promise<Error> {
  const body = (await r.json().catch(() => ({}))) as { detail?: string };
  return new Error(body.detail ?? fallback);
}

export async function patchEvent(
  eventId: string,
  body: { updates: Record<string, string | number | null>; reason?: string },
): Promise<EventPatchResponse> {
  const r = await fetch(`/events/${eventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw await unwrapError(r, "event update failed");
  return r.json();
}

export async function listEventOverrides(
  eventId: string,
): Promise<EventOverridesResponse> {
  const r = await fetch(`/events/${eventId}/overrides`);
  if (!r.ok) throw await unwrapError(r, "list overrides failed");
  return r.json();
}

export async function clearEventOverride(
  eventId: string,
  field: string,
  reason: string = "",
): Promise<EventOverrideClearResponse> {
  const r = await fetch(`/events/${eventId}/overrides/${field}/clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!r.ok) throw await unwrapError(r, "clear override failed");
  return r.json();
}

export async function listEventHistory(
  eventId: string,
  limit: number = 50,
): Promise<EventChangeHistoryResponse> {
  const r = await fetch(`/events/${eventId}/history?limit=${limit}`);
  if (!r.ok) throw await unwrapError(r, "list history failed");
  return r.json();
}
