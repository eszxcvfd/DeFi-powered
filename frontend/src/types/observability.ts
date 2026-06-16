export type AlertRule = {
  id: string;
  organization_id: string;
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  window_seconds: number;
  severity: string;
  cooldown_seconds: number;
  channels: string[];
  enabled: boolean;
  is_system: boolean;
  sort_order: number;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
};

export type AlertRuleList = {
  items: AlertRule[];
};

export type AlertEvent = {
  id: string;
  organization_id: string;
  rule_id: string;
  rule_name: string;
  metric: string;
  status: string;
  severity: string;
  fired_at: string;
  resolved_at: string | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolution_note: string | null;
  correlation_id: string;
  dedup_key: string;
  payload: Record<string, unknown>;
  payload_redacted: boolean;
};

export type AlertEventList = {
  items: AlertEvent[];
  total: number;
  limit: number;
  offset: number;
};

export type GateCheck = {
  name: string;
  detail: string;
};

export type OperatorSummary = {
  environment_mode: string;
  gate_passed: boolean;
  gate_blocking: GateCheck[];
  gate_warnings: GateCheck[];
  backup_freshness: string;
  backup_age_hours: number | null;
  worker_heartbeat_age_seconds: number | null;
  open_alerts_by_severity: Record<string, number>;
  recent_alerts: AlertEvent[];
  rules_total: number;
  rules_enabled: number;
};
