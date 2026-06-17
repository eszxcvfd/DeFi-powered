// Webhook API client (US-049).
//
// Wraps the bounded REST surface the
// `WebhookDeliveryService` exposes. The client
// keeps the subscription CRUD, the secret
// rotation, the test send, the delivery list,
// and the delivery retry in a single module
// so the operator panel widget consumes one
// import.

const jsonHeaders = { "Content-Type": "application/json" };

function adminHeaders(): HeadersInit {
  return { ...jsonHeaders, "X-Actor-Role": "admin" };
}

export type WebhookEventTypeValue =
  | "event.high_priority"
  | "lead.stage_changed"
  | "lead.outcome_changed"
  | "discovery.job_failed"
  | "connector.auto_disable_triggered"
  | "connector.auto_disable_recovered"
  | "alert.fired";

export type WebhookDeliveryStatusValue =
  | "pending"
  | "in_flight"
  | "succeeded"
  | "failed"
  | "dead_letter"
  | "cancelled";

export interface WebhookEventTypeChoice {
  value: WebhookEventTypeValue;
  label: string;
}

export interface WebhookDeliveryStatusChoice {
  value: WebhookDeliveryStatusValue;
  label: string;
}

export interface WebhookChoices {
  event_types: WebhookEventTypeChoice[];
  delivery_statuses: WebhookDeliveryStatusChoice[];
}

export interface WebhookSubscriptionView {
  id: string;
  organization_id: string;
  name: string;
  target_url: string;
  secret_id: string;
  event_types: string[];
  enabled: boolean;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
  last_rotated_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
}

export interface WebhookDeliveryView {
  id: string;
  organization_id: string;
  subscription_id: string;
  event_id: string | null;
  event_type: WebhookEventTypeValue | string;
  target_url: string;
  payload_hash: string;
  status: WebhookDeliveryStatusValue | string;
  attempt_count: number;
  next_attempt_at: string | null;
  last_attempt_at: string | null;
  last_response_code: number | null;
  last_response_message: string | null;
  delivered_at: string | null;
  created_at: string | null;
}

export interface WebhookSubscriptionListResponse {
  items: WebhookSubscriptionView[];
  total: number;
  limit: number;
  offset: number;
}

export interface WebhookDeliveryListResponse {
  items: WebhookDeliveryView[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateSubscriptionPayload {
  name: string;
  target_url: string;
  event_types: string[];
  enabled?: boolean;
}

export interface UpdateSubscriptionPayload {
  name?: string;
  target_url?: string;
  event_types?: string[];
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

export async function listWebhookChoices(): Promise<WebhookChoices> {
  const res = await fetch("/admin/webhooks/choices", {
    headers: adminHeaders(),
  });
  return unwrap<WebhookChoices>(res);
}

export async function listWebhookSubscriptions(
  enabled?: boolean
): Promise<WebhookSubscriptionListResponse> {
  const params = new URLSearchParams();
  if (enabled !== undefined) params.set("enabled", String(enabled));
  const url = params.toString()
    ? `/admin/webhooks/subscriptions?${params}`
    : "/admin/webhooks/subscriptions";
  const res = await fetch(url, { headers: adminHeaders() });
  return unwrap<WebhookSubscriptionListResponse>(res);
}

export async function createWebhookSubscription(
  payload: CreateSubscriptionPayload
): Promise<WebhookSubscriptionView> {
  const res = await fetch("/admin/webhooks/subscriptions", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  });
  return unwrap<WebhookSubscriptionView>(res);
}

export async function updateWebhookSubscription(
  subscriptionId: string,
  payload: UpdateSubscriptionPayload
): Promise<WebhookSubscriptionView> {
  const res = await fetch(
    `/admin/webhooks/subscriptions/${subscriptionId}`,
    {
      method: "PATCH",
      headers: adminHeaders(),
      body: JSON.stringify(payload),
    }
  );
  return unwrap<WebhookSubscriptionView>(res);
}

export async function deleteWebhookSubscription(
  subscriptionId: string
): Promise<void> {
  const res = await fetch(
    `/admin/webhooks/subscriptions/${subscriptionId}`,
    { method: "DELETE", headers: adminHeaders() }
  );
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export async function rotateWebhookSecret(
  subscriptionId: string
): Promise<WebhookSubscriptionView> {
  const res = await fetch(
    `/admin/webhooks/subscriptions/${subscriptionId}/rotate-secret`,
    { method: "POST", headers: adminHeaders() }
  );
  return unwrap<WebhookSubscriptionView>(res);
}

export async function testWebhookSubscription(
  subscriptionId: string
): Promise<WebhookDeliveryView> {
  const res = await fetch(
    `/admin/webhooks/subscriptions/${subscriptionId}/test`,
    { method: "POST", headers: adminHeaders() }
  );
  return unwrap<WebhookDeliveryView>(res);
}

export async function listWebhookDeliveries(
  subscriptionId?: string,
  status?: string
): Promise<WebhookDeliveryListResponse> {
  const params = new URLSearchParams();
  if (subscriptionId) params.set("subscription_id", subscriptionId);
  if (status) params.set("status", status);
  const url = params.toString()
    ? `/admin/webhooks/deliveries?${params}`
    : "/admin/webhooks/deliveries";
  const res = await fetch(url, { headers: adminHeaders() });
  return unwrap<WebhookDeliveryListResponse>(res);
}

export async function retryWebhookDelivery(
  deliveryId: string
): Promise<WebhookDeliveryView> {
  const res = await fetch(
    `/admin/webhooks/deliveries/${deliveryId}/retry`,
    { method: "POST", headers: adminHeaders() }
  );
  return unwrap<WebhookDeliveryView>(res);
}
