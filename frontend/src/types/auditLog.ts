export type AuditActor = {
  actor_id: string;
  actor_type: string;
  role: string;
};

export type AuditTarget = {
  target_type: string;
  target_id: string;
  display: string;
};

export type AuditEntry = {
  id: string;
  organization_id: string;
  actor: AuditActor;
  action: string;
  action_family: string;
  target: AuditTarget;
  outcome: string;
  occurred_at: string;
  context: Record<string, string>;
  metadata: Record<string, unknown>;
  metadata_redacted: boolean;
};

export type AuditList = {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditFilterOptions = {
  actor_types: string[];
  outcomes: string[];
  action_families: string[];
  target_types: string[];
};
