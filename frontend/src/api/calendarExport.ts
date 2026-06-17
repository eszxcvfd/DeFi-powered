// Calendar export API client (US-045).
//
// Talks to the bounded calendar export surface on the
// backend. The client never persists the plaintext
// token; the caller is expected to copy the
// plaintext into a calendar subscription URL and
// discard it.

import { apiClient, type ApiError } from "@/lib/apiClient";

export type CalendarScope = "event" | "watchlist" | "event_filter";

export type CalendarExportToken = {
  id: string;
  organization_id: string;
  user_id: string;
  scope: CalendarScope;
  target_id: string | null;
  filter_json: Record<string, unknown> | null;
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
  use_count: number;
  created_at: string | null;
  updated_at: string | null;
};

export type CalendarExportTokenWithPlaintext = CalendarExportToken & {
  plaintext: string;
};

export type CalendarExportAudit = {
  id: string;
  organization_id: string;
  user_id: string | null;
  token_id: string | null;
  scope: CalendarScope;
  event_id: string | null;
  event_count: number;
  result: string;
  ip_address: string;
  user_agent: string;
  request_id: string;
  created_at: string | null;
};

function readApiError(err: unknown): string {
  const apiError = err as ApiError;
  return apiError?.message || String(err);
}

export async function mintCalendarExportToken(payload: {
  scope: CalendarScope;
  target_id?: string | null;
  filter_json?: Record<string, unknown> | null;
  expires_at?: string | null;
}): Promise<CalendarExportTokenWithPlaintext> {
  try {
    const r = await apiClient.post<CalendarExportTokenWithPlaintext>(
      "/calendar-export-tokens",
      payload,
    );
    return r;
  } catch (err) {
    throw new Error(`mintCalendarExportToken: ${readApiError(err)}`);
  }
}

export async function listCalendarExportTokens(params?: {
  include_revoked?: boolean;
  limit?: number;
}): Promise<{ items: CalendarExportToken[]; total: number }> {
  try {
    const r = await apiClient.get<{ items: CalendarExportToken[]; total: number }>(
      "/calendar-export-tokens",
      { params: params ?? {} },
    );
    return r;
  } catch (err) {
    throw new Error(`listCalendarExportTokens: ${readApiError(err)}`);
  }
}

export async function revokeCalendarExportToken(
  tokenId: string,
): Promise<CalendarExportToken> {
  try {
    const r = await apiClient.delete<CalendarExportToken>(
      `/calendar-export-tokens/${tokenId}`,
    );
    return r;
  } catch (err) {
    throw new Error(`revokeCalendarExportToken: ${readApiError(err)}`);
  }
}

export async function listCalendarExportAudits(params?: {
  limit?: number;
}): Promise<{ items: CalendarExportAudit[]; total: number }> {
  try {
    const r = await apiClient.get<{ items: CalendarExportAudit[]; total: number }>(
      "/calendar-export-tokens/audits",
      { params: params ?? {} },
    );
    return r;
  } catch (err) {
    throw new Error(`listCalendarExportAudits: ${readApiError(err)}`);
  }
}

export function eventIcsUrl(eventId: string): string {
  return `${apiClient.defaults.baseURL}/events/${eventId}.ics`;
}

export function watchlistIcsUrl(): string {
  return `${apiClient.defaults.baseURL}/watchlist/events.ics`;
}

export function tokenizedIcsUrl(plaintext: string): string {
  return `${apiClient.defaults.baseURL}/calendar-export/${plaintext}.ics`;
}
