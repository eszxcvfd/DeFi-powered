export type DiscoveryCopilotResponse = {
  id: string;
  campaign_id: string;
  question: string;
  confidence: number;
  provider_id: string;
  model_id: string;
  structured: {
    claims: { text: string; confidence?: number | null }[];
    evidence: { summary: string; source_ref?: string | null }[];
    confidence: number;
    assumptions: string[];
    risk_flags: { code: string; message: string }[];
    proposed_query_framing: string[];
    recommended_source_ids: string[];
  };
  accepted_at: string | null;
  query_expansion_set_id: string | null;
  created_at: string;
  viewer_feedback?: import("@/types/aiFeedback").ViewerFeedback | null;
};

export type AcceptCopilotResult = {
  copilot_response_id: string;
  query_expansion_set_id: string;
  expansion_status: string;
};