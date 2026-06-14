export type EventScoreSummary = {
  total_score: number | null;
  priority_level: string | null;
  scoring_version: string | null;
  calculated_at: string | null;
  score_state: "missing" | "ready";
};

export type CampaignEventListItem = {
  id: string;
  campaign_id: string;
  campaign_name?: string;
  canonical_title: string;
  source_url: string;
  observed_at: string;
  region: string;
  confidence_summary: string;
  observation_count: number;
  source_count: number;
  discovery_job_id: string | null;
  score?: EventScoreSummary | null;
  deferred?: Record<string, string>;
};

export type FieldConfidence = {
  field: string;
  trust: string;
  note: string;
};

export type EventProvenance = {
  confidence_summary: string;
  field_confidence: FieldConfidence[];
  merge_notes: { at?: string; note: string }[];
  observation_count: number;
  source_ids: string[];
};

export type ScoreComponent = {
  key: string;
  raw_value: number;
  weighted_contribution: number;
  evidence: string;
  missing_data: string[];
};

export type EventScoreDetail = {
  total_score: number;
  priority_level: string;
  scoring_version: string;
  calculated_at: string;
  weights_snapshot: Record<string, number>;
  components: ScoreComponent[];
  missing_fields: string[];
  score_reducers: string[];
};

export type AudienceEvidence = {
  cue: string;
  kind: string;
  detail: string;
  source_field: string;
};

export type AudienceHypothesis = {
  id: string;
  segment_name: string;
  fit_type: string;
  reason: string;
  confidence: number;
  generated_by: string;
  model_version: string;
  evidence: AudienceEvidence[];
};

export type AudienceAnalysis = {
  state: string;
  hypotheses: AudienceHypothesis[];
  generation_notes: string[];
  strategy_version: string;
};

export type EngagementTask = {
  id: string;
  phase: string;
  title: string;
  rationale: string;
  status: string;
  assignee: string;
  deadline: string | null;
  notes: string;
};

export type EngagementPlanState = {
  state: string;
  plan: { id: string; strategy_version: string; created_at: string | null; updated_at: string | null } | null;
  tasks: EngagementTask[];
  generation_notes: string[];
};

export type GeneratedContentSummary = {
  id: string;
  variant_index: number;
  content_type: string;
  platform: string;
  review_status: string;
  ready_for_use: boolean;
  body_preview: string;
  risk_flag_count: number;
  last_editor: string;
};

export type EventLeadLink = {
  linked_count: number;
  linked_lead_ids: string[];
  has_linked_lead: boolean;
};

export type EventDetail = {
  id: string;
  campaign_id: string;
  canonical_title: string;
  source_url: string;
  observed_at: string;
  description: string;
  organizer: string;
  region: string;
  starts_at: string | null;
  discovery_job_id: string | null;
  provenance: EventProvenance;
  observations: {
    id: string;
    source_id: string;
    source_url: string;
    observed_at: string;
    raw_title: string;
    discovery_job_id: string | null;
  }[];
  score: EventScoreDetail | null;
  score_state: string;
  audience: AudienceAnalysis;
  engagement: EngagementPlanState;
  generated_content: GeneratedContentSummary[];
  leads: EventLeadLink;
  deferred: Record<string, string>;
};