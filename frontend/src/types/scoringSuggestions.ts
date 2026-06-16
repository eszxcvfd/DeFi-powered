export type ScoringSuggestionSignal = {
  kind: string;
  summary: string;
  count: number;
  reason_code?: string | null;
};

export type ScoringWeightDelta = {
  component: string;
  current_weight: number;
  proposed_weight: number;
  delta: number;
  rationale: string;
};

export type ScoringSuggestionSet = {
  id: string;
  campaign_id: string;
  status: string;
  confidence: number;
  summary: string;
  caution_notes: string[];
  assumptions: string[];
  signals: ScoringSuggestionSignal[];
  deltas: ScoringWeightDelta[];
  current_weights: Record<string, number>;
  proposed_weights: Record<string, number>;
  generated_by?: string | null;
  decided_by?: string | null;
  decided_at?: string | null;
  review_note?: string | null;
  weight_snapshot_id?: string | null;
  created_at?: string | null;
};

export type ScoringSuggestionApproveResponse = {
  suggestion: ScoringSuggestionSet;
  campaign: { scoring_weights: Record<string, number> };
};