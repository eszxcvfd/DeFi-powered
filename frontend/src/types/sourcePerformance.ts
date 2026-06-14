export type SourcePerformanceGrouping = "platform" | "connector" | "campaign" | "industry";

export type SourcePerformanceMetrics = {
  events_discovered: number;
  events_prioritized: number;
  leads_created: number;
  opportunities: number;
};

export type SourcePerformanceRow = {
  group_key: string;
  group_label: string;
  metrics: SourcePerformanceMetrics;
};

export type SourcePerformanceReport = {
  grouping: SourcePerformanceGrouping;
  grouping_label: string;
  window: { start: string; end: string; preset: string | null };
  rows: SourcePerformanceRow[];
  unattributed: {
    events_without_source_link: number;
    leads_without_group_key: number;
    explanation: string;
  } | null;
  freshness: { last_updated_at: string | null; source: string };
  generated_at: string;
};