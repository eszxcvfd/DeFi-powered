export type DiscoveryJob = {
  id: string;
  campaign_id: string;
  status: string;
  progress: {
    percent?: number;
    sources?: Record<string, { status: string; items_found?: number }>;
    events?: { type: string }[];
  };
  error_summary: string | null;
  cancel_requested: boolean;
  criteria_snapshot: Record<string, unknown>;
};