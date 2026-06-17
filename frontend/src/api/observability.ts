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

// US-040 Cutover API Callers
export async function enterPilotLive(payload: { reason: string; notes?: string; admin_pin?: string }) {
  const r = await fetch("/admin/cutover/enter-pilot-live", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function pauseEnvironment(payload: { reason: string; notes?: string }) {
  const r = await fetch("/admin/cutover/pause", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function rollbackEnvironment(payload: { reason: string; notes?: string; target_mode: string }) {
  const r = await fetch("/admin/cutover/rollback", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listCutoverEvents() {
  const r = await fetch("/admin/cutover/events", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// US-042 Metrics API Callers
export async function getExportPolicy() {
  const r = await fetch("/admin/observability/export-policy", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateExportPolicy(payload: any) {
  const r = await fetch("/admin/observability/export-policy", {
    method: "PUT",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function testExportPolicy() {
  const r = await fetch("/admin/observability/export-policy/test", {
    method: "POST",
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// US-043 Backups & Data Deletion API Callers
export async function getRetentionPolicy() {
  const r = await fetch("/admin/retention/policy", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateRetentionPolicy(payload: any) {
  const r = await fetch("/admin/retention/policy", {
    method: "PUT",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function pruneExpiredBackups() {
  const r = await fetch("/admin/retention/prune", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify({}),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function dryRunRestore(backupId: string) {
  const r = await fetch(`/admin/backup-snapshots/${backupId}:restore:dry-run`, {
    method: "POST",
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function rehearsalRestore(backupId: string) {
  const r = await fetch(`/admin/backup-snapshots/${backupId}:rehearsal`, {
    method: "POST",
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteData(payload: { target: string; target_id: string; accepted_by: string; reason: string }) {
  const r = await fetch("/admin/data-deletion", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// US-044 Performance API Callers
export async function getPerformanceSummary() {
  const r = await fetch("/admin/performance/summary", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function runPerformanceScenario(scenario: string) {
  const r = await fetch("/admin/performance/scenarios:run", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify({ scenario }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// US-046 Connector Health API Callers
export async function getConnectorHealthSummary() {
  const r = await fetch("/admin/connectors/health/summary", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function computeConnectorHealthSnapshot(sourceId: string) {
  const r = await fetch("/admin/connectors/health/snapshots:compute", {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify({ source_id: sourceId }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getConnectorHealthErrors(sourceId: string) {
  const r = await fetch(`/admin/connectors/health/${sourceId}/errors`, {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listBackupSnapshots() {
  const r = await fetch("/admin/backup-snapshots", {
    headers: ownerHeaders(),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function verifyBackupSnapshot(backupId: string, status: string) {
  const r = await fetch(`/admin/backup-snapshots/${backupId}:verify`, {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify({ status }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function restoreBackupSnapshot(backupId: string, acceptedBy: string) {
  const r = await fetch(`/admin/backup-snapshots/${backupId}:restore`, {
    method: "POST",
    headers: ownerHeaders(),
    body: JSON.stringify({ accepted_by: acceptedBy }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

