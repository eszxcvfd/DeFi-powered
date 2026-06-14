export type BrowserActionPreview = {
  action_type: string;
  title: string;
  impact_summary: string;
  target_url?: string;
  source_name?: string;
  parameters_summary?: Record<string, unknown>;
};

export type BrowserActionResult = {
  action_type: string;
  lifecycle: string;
  summary: string;
  detail?: string | null;
  policy_reason?: string | null;
  current_url?: string | null;
  text_preview?: string | null;
  confirmation_id?: string | null;
  confirmation_state?: string | null;
  preview?: BrowserActionPreview | null;
  expires_at?: string | null;
  requested_by?: string | null;
};

export async function runBrowserAction(
  sessionId: string,
  actionType: string,
  parameters: Record<string, unknown> = {},
): Promise<BrowserActionResult> {
  const r = await fetch(`/browser-sessions/${sessionId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_type: actionType, parameters }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "browser action failed");
  }
  return r.json();
}

export async function confirmBrowserAction(
  sessionId: string,
  confirmationId: string,
): Promise<BrowserActionResult> {
  const r = await fetch(
    `/browser-sessions/${sessionId}/confirmations/${confirmationId}/confirm`,
    { method: "POST", headers: { "Content-Type": "application/json" } },
  );
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "confirm failed");
  }
  return r.json();
}

export async function cancelBrowserAction(
  sessionId: string,
  confirmationId: string,
): Promise<BrowserActionResult> {
  const r = await fetch(
    `/browser-sessions/${sessionId}/confirmations/${confirmationId}/cancel`,
    { method: "POST", headers: { "Content-Type": "application/json" } },
  );
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "cancel failed");
  }
  return r.json();
}