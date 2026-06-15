import type {
  InboxResponse,
  NotificationState,
  NotificationView,
  PreferencesResponse,
  ScanResponse,
} from "@/types/notifications";

async function parseError(r: Response): Promise<never> {
  const text = await r.text();
  try {
    const json = JSON.parse(text);
    if (json && typeof json === "object" && "detail" in json) {
      throw new Error(typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail));
    }
  } catch (e) {
    if (e instanceof Error) throw e;
  }
  throw new Error(text || "notification request failed");
}

export async function listNotifications(
  state: NotificationState | null = null,
): Promise<InboxResponse> {
  const url = state ? `/notifications?state=${state}` : "/notifications";
  const r = await fetch(url, { credentials: "same-origin" });
  if (!r.ok) await parseError(r);
  return (await r.json()) as InboxResponse;
}

export async function markRead(id: string): Promise<NotificationView> {
  const r = await fetch(`/notifications/${id}/read`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as NotificationView;
}

export async function dismissNotification(id: string): Promise<NotificationView> {
  const r = await fetch(`/notifications/${id}/dismiss`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as NotificationView;
}

export async function getPreferences(): Promise<PreferencesResponse> {
  const r = await fetch("/notification-preferences", { credentials: "same-origin" });
  if (!r.ok) await parseError(r);
  return (await r.json()) as PreferencesResponse;
}

export async function updatePreferences(
  preferences: Record<string, Record<string, boolean>>,
): Promise<PreferencesResponse> {
  const r = await fetch("/notification-preferences", {
    method: "PATCH",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preferences }),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as PreferencesResponse;
}

export async function runScan(input: {
  include_reminders?: boolean;
  include_events?: boolean;
  lead_minutes?: number;
} = {}): Promise<ScanResponse> {
  const r = await fetch("/admin/notifications/scan", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      include_reminders: input.include_reminders ?? true,
      include_events: input.include_events ?? true,
      lead_minutes: input.lead_minutes ?? 60,
    }),
  });
  if (!r.ok) await parseError(r);
  return (await r.json()) as ScanResponse;
}
