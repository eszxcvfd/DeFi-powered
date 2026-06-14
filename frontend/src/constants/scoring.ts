export const DEFAULT_SCORING_WEIGHTS: Record<string, number> = {
  topic_relevance: 0.25,
  icp_match: 0.2,
  organizer_reputation: 0.1,
  speaker_relevance: 0.1,
  audience_quality: 0.1,
  engagement_accessibility: 0.08,
  replay_availability: 0.07,
  geographic_fit: 0.05,
  timing_fit: 0.05,
};

export const SCORING_LABELS: Record<string, string> = {
  topic_relevance: "Topic relevance",
  icp_match: "ICP match",
  organizer_reputation: "Organizer reputation",
  speaker_relevance: "Speaker relevance",
  audience_quality: "Audience quality",
  engagement_accessibility: "Engagement accessibility",
  replay_availability: "Replay availability",
  geographic_fit: "Geographic fit",
  timing_fit: "Timing fit",
};