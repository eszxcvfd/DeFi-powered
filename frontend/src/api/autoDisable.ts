// Auto-disable API client (US-048).
//
// Wraps the bounded REST surface the
// `AutoDisableService` exposes. The client
// keeps the source-side helper, the rule CRUD,
// the event list, and the recovery flow in a
// single module so the operator panel widget
// consumes one import.

const jsonHeaders = { "Content-Type": "application/json" };

function adminHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "admin" };
}

export type AutoDisableTriggerValue =
  | "health_unhealthy"
  | "captcha_rate_breach"
  | "failure_rate_breach"
  | "needs_user_action_storm"
  | "error_spike"
  | "manual_kill_switch";

export type AutoDisableEventStatusValue =
  | "active"
  | "recovering"
  | "resolved"
  | "superseded";

export interface AutoDisableTriggerChoice {
  value: AutoDisableTriggerValue;
  label: string;
}

export interface AutoDisableEventStatusChoice {
  value: AutoDisableEventStatusValue;
  label: string;
}

export interface AutoDisableChoices {
  triggers: AutoDisableTriggerChoice[];
  event_statuses: AutoDisableEventStatusChoice[];
}

export interface AutoDisableRuleView {
  id: string;
  organization_id: string;
  source_id: string;
  trigger: AutoDisableTriggerValue;
  threshold_value: number;
  window_seconds: number;
  consecutive_breaches: number;
  cooldown_seconds: number;
  enabled: boolean;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AutoDisableEventView {
  id: string;
  organization_id: string;
  source_id: string;
  trigger: AutoDisableTriggerValue;
  reason: string;
  breach_count: number;
  window_start: string | null;
  window_end: string | null;
  status: AutoDisableEventStatusValue;
  alert_event_id: string | null;
  health_snapshot_id: string | null;
  recovery_actor_id: string | null;
  recovery_reason: string | null;
  recovered_at: string | null;
  audit_correlation_id: string;
  created_at: string | null;
}

export interface AutoDisableEvaluationResultView {
  should_disable: boolean;
  trigger: AutoDisableTriggerValue | null;
  reason: string | null;
  breach_count: number;
  window_start: string | null;
  window_end: string | null;
  alert_event_id: string | null;
  health_snapshot_id: string | null;
  rule_id: string | null;
}

export interface AutoDisableRuleListResponse {
  items: AutoDisableRuleView[];
  total: number;
  limit: number;
  offset: number;
}

export interface AutoDisableEventListResponse {
  items: AutoDisableEventView[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateRulePayload {
  source_id: string;
  trigger: AutoDisableTriggerValue;
  threshold_value: number;
  window_seconds?: number;
  consecutive_breaches?: number;
  cooldown_seconds?: number;
  enabled?: boolean;
}

export interface UpdateRulePayload {
  threshold_value?: number;
  window_seconds?: number;
  consecutive_breaches?: number;
  cooldown_seconds?: number;
  enabled?: boolean;
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // ignore parse error
    }
    throw new Error(
      typeof detail === "string" ? detail : `HTTP ${res.status}`
    );
  }
  return (await res.json()) as T;
}

export async function listAutoDisableChoices(): Promise<AutoDisableChoices> {
  const res = await fetch(
    "/admin/connectors/auto-disable/choices",
    { headers: adminHeaders() }
  );
  return unwrap<AutoDisableChoices>(res);
}

export async function listAutoDisableRules(
  sourceId?: string
): Promise<AutoDisableRuleListResponse> {
  const params = new URLSearchParams();
  if (sourceId) params.set("source_id", sourceId);
  const url = params.toString()
    ? `/admin/connectors/auto-disable/rules?${params}`
    : "/admin/connectors/auto-disable/rules";
  const res = await fetch(url, { headers: adminHeaders() });
  return unwrap<AutoDisableRuleListResponse>(res);
}

export async function createAutoDisableRule(
  payload: CreateRulePayload
): Promise<AutoDisableRuleView> {
  const res = await fetch("/admin/connectors/auto-disable/rules", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  });
  return unwrap<AutoDisableRuleView>(res);
}

export async function updateAutoDisableRule(
  ruleId: string,
  payload: UpdateRulePayload
): Promise<AutoDisableRuleView> {
  const res = await fetch(
    `/admin/connectors/auto-disable/rules/${ruleId}`,
    {
      method: "PATCH",
      headers: adminHeaders(),
      body: JSON.stringify(payload),
    }
  );
  return unwrap<AutoDisableRuleView>(res);
}

export async function deleteAutoDisableRule(ruleId: string): Promise<void> {
  const res = await fetch(
    `/admin/connectors/auto-disable/rules/${ruleId}`,
    { method: "DELETE", headers: adminHeaders() }
  );
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export async function listAutoDisableEvents(
  sourceId?: string
): Promise<AutoDisableEventListResponse> {
  const params = new URLSearchParams();
  if (sourceId) params.set("source_id", sourceId);
  const url = params.toString()
    ? `/admin/connectors/auto-disable/events?${params}`
    : "/admin/connectors/auto-disable/events";
  const res = await fetch(url, { headers: adminHeaders() });
  return unwrap<AutoDisableEventListResponse>(res);
}

export async function recoverAutoDisableEvent(
  eventId: string,
  reason: string
): Promise<AutoDisableEventView> {
  const res = await fetch(
    `/admin/connectors/auto-disable/events/${eventId}/recover`,
    {
      method: "POST",
      headers: adminHeaders(),
      body: JSON.stringify({ reason }),
    }
  );
  return unwrap<AutoDisableEventView>(res);
}

export async function evaluateAutoDisable(
  sourceId: string
): Promise<AutoDisableEvaluationResultView> {
  const res = await fetch(
    `/admin/connectors/${sourceId}/auto-disable/evaluate`,
    { method: "POST", headers: adminHeaders() }
  );
  return unwrap<AutoDisableEvaluationResultView>(res);
}
