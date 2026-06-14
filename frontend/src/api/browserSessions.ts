import { formatApiErrorDetail } from "@/lib/apiError";

export type BrowserSessionView = {
  id: string;
  state: string;
  engine: string;
  current_url: string;
  runtime_seconds: number;
  latest_action_summary: string;
  isolation: { isolation_key: string; profile_boundary: string };
  target: {
    kind: string;
    event_id: string | null;
    source_id: string;
    source_name: string;
    source_domain: string;
    initial_url: string;
  };
  stop_requested: boolean;
  terminal: boolean;
  error_summary: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  debug_enabled?: boolean;
  latest_artifact_summary?: string;
};

export async function createBrowserSessionForEvent(
  eventId: string,
  sourceId: string,
): Promise<BrowserSessionView> {
  const r = await fetch("/browser-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, source_id: sourceId }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(
      formatApiErrorDetail((body as { detail?: unknown }).detail, "browser session create failed"),
    );
  }
  return r.json();
}

export async function getBrowserSession(sessionId: string): Promise<BrowserSessionView> {
  const r = await fetch(`/browser-sessions/${sessionId}`);
  if (!r.ok) throw new Error("browser session status failed");
  return r.json();
}

export async function createBrowserSessionForSource(
  sourceId: string,
  initialUrl: string,
): Promise<BrowserSessionView> {
  const r = await fetch("/browser-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId, initial_url: initialUrl }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(
      formatApiErrorDetail((body as { detail?: unknown }).detail, "browser session create failed"),
    );
  }
  return r.json();
}

export async function stopBrowserSession(sessionId: string): Promise<BrowserSessionView> {
  const r = await fetch(`/browser-sessions/${sessionId}/stop`, { method: "POST" });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "browser session stop failed");
  }
  return r.json();
}