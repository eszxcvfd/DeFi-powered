export type DiscoverySchedule = {
  id: string;
  campaign_id: string;
  enabled_state: string;
  recurrence: Record<string, unknown>;
  recurrence_summary: string;
  timezone: string;
  next_run_at: string | null;
  source_ids: string[];
  latest_job: { job_id: string; status: string; error_summary: string | null } | null;
  last_dispatch_outcome: string | null;
};