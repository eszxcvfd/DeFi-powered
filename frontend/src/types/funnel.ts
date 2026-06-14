export type FunnelCohort = {
  start: string;
  end: string;
  preset: string | null;
  rule: string;
};

export type FunnelStep = {
  key: string;
  label: string;
  count: number;
  note: string | null;
};

export type UnattributedLeadSummary = {
  manual_leads_in_cohort: number;
  explanation: string;
};

export type FunnelReport = {
  cohort: FunnelCohort;
  steps: FunnelStep[];
  unattributed: UnattributedLeadSummary | null;
  freshness: { last_updated_at: string | null; source: string };
  generated_at: string;
};