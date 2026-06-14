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
  deferred: Record<string, string>;
};