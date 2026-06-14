export type ContentEffectivenessGrouping = "content_type" | "tone" | "template";

export type ContentEffectivenessMetrics = {
  content_used: number;
  outcomes_linked: number;
  outcomes_contact: number;
  outcomes_response: number;
  outcomes_meeting: number;
  outcomes_opportunity: number;
};

export type ContentEffectivenessRow = {
  group_key: string;
  group_label: string;
  metrics: ContentEffectivenessMetrics;
};

export type ContentEffectivenessReport = {
  grouping: ContentEffectivenessGrouping;
  grouping_label: string;
  window: { start: string; end: string; preset: string | null };
  rows: ContentEffectivenessRow[];
  unattributed: {
    used_content_without_metadata: number;
    outcomes_without_content_link: number;
    explanation: string;
  } | null;
  freshness: { last_updated_at: string | null; source: string };
  correlation_note: string;
  generated_at: string;
};