export type BrowserArtifactView = {
  id: string;
  session_id: string;
  artifact_type: string;
  capture_mode: string;
  status: string;
  content_type: string;
  byte_size: number;
  captured_by: string;
  summary: string;
  redacted: boolean;
  expires_at: string;
  created_at?: string | null;
  policy_reason?: string | null;
};

export async function setBrowserDebug(sessionId: string, enabled: boolean): Promise<{ debug_enabled: boolean }> {
  const r = await fetch(`/browser-sessions/${sessionId}/debug`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!r.ok) throw new Error("debug toggle failed");
  return r.json();
}

export async function captureBrowserScreenshot(sessionId: string): Promise<BrowserArtifactView> {
  const r = await fetch(`/browser-sessions/${sessionId}/artifacts/screenshot`, { method: "POST" });
  if (!r.ok) throw new Error("screenshot failed");
  return r.json();
}

export async function listBrowserArtifacts(sessionId: string): Promise<BrowserArtifactView[]> {
  const r = await fetch(`/browser-sessions/${sessionId}/artifacts`);
  if (!r.ok) throw new Error("list artifacts failed");
  return r.json();
}

export async function fetchArtifactObjectUrl(sessionId: string, artifactId: string): Promise<string> {
  const r = await fetch(`/browser-sessions/${sessionId}/artifacts/${artifactId}/download`);
  if (!r.ok) throw new Error("artifact download failed");
  const blob = await r.blob();
  return URL.createObjectURL(blob);
}