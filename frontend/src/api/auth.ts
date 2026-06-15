import type { AuthBootstrap, AuthBootstrapStatus, AuthSession, LoginRequest, LoginResponse } from "@/types/auth";

const jsonHeaders = { "Content-Type": "application/json" };

export async function login(payload: LoginRequest): Promise<{ session: AuthSession; cookies: string }> {
  const r = await fetch("/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(detail || "login failed");
  }
  const body: LoginResponse = await r.json();
  const cookies = r.headers.get("set-cookie") || "";
  return { session: body.session, cookies };
}

export async function logout(): Promise<void> {
  await fetch("/auth/logout", { method: "POST", credentials: "same-origin" });
}

export async function refreshSession(): Promise<AuthSession> {
  const r = await fetch("/auth/refresh", { method: "POST", credentials: "same-origin" });
  if (!r.ok) throw new Error("refresh failed");
  const body: LoginResponse = await r.json();
  return body.session;
}

export async function getMe(): Promise<AuthSession> {
  const r = await fetch("/auth/me", { credentials: "same-origin" });
  if (!r.ok) throw new Error("not authenticated");
  return (await r.json()) as AuthSession;
}

export async function getBootstrapStatus(): Promise<AuthBootstrapStatus> {
  const r = await fetch("/auth/bootstrap-status", { credentials: "same-origin" });
  if (!r.ok) throw new Error("bootstrap status failed");
  return (await r.json()) as AuthBootstrapStatus;
}

export async function getAuthBootstrap(): Promise<AuthBootstrap> {
  try {
    const session = await getMe();
    return { authenticated: true, session };
  } catch {
    return { authenticated: false };
  }
}
