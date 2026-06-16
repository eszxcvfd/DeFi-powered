import type {
  AlertEvent,
  AlertEventList,
  AlertRule,
  AlertRuleList,
  OperatorSummary,
} from "@/types/observability";

const jsonHeaders = { "Content-Type": "application/json" };

function ownerHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "owner" };
}

function buildQuery(params: Record<string, string | number | null | undefined>): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export async function getOperatorSummary(): Promise<OperatorSummary> {
  const r = await fetch("/admin/observability/summary", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listAlertRules(): Promise<AlertRuleList> {
  const r = await fetch("/admin/observability/alert-rules", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type AlertRuleCreatePayload = {
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  window_seconds: number;
  severity: string;
  cooldown_seconds: number;
  channels: string[];
  enabled: boolean;
};

export async function createAlertRule(
  payload: AlertRuleCreatePayload,
): Promise<AlertRule> {
  const r = await fetch("/admin/observability/alert-rules", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type AlertRuleUpdatePayload = {
  threshold?: number;
  window_seconds?: number;
  severity?: string;
  cooldown_seconds?: number;
  channels?: string[];
  enabled?: boolean;
};

export async function updateAlertRule(
  ruleId: string,
  payload: AlertRuleUpdatePayload,
): Promise<AlertRule> {
  const r = await fetch(`/admin/observability/alert-rules/${ruleId}`, {
    method: "PATCH",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  const r = await fetch(`/admin/observability/alert-rules/${ruleId}`, {
    method: "DELETE",
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function listAlertEvents(params: {
  status?: string;
  severity?: string;
  rule_id?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<AlertEventList> {
  const r = await fetch(`/admin/observability/alert-events${buildQuery(params)}`, {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function acknowledgeAlertEvent(eventId: string): Promise<AlertEvent> {
  const r = await fetch(
    `/admin/observability/alert-events/${eventId}/acknowledge`,
    { method: "POST", headers: ownerHeaders() },
  );
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
