export type ViewerFeedback = {
  state: string;
  reason_code: string | null;
  note: string | null;
  updated_at: string | null;
};

export const AI_FEEDBACK_REASONS = [
  { value: "low_evidence", label: "Low evidence" },
  { value: "wrong_audience_fit", label: "Wrong audience fit" },
  { value: "weak_usefulness", label: "Weak usefulness" },
  { value: "misleading", label: "Misleading" },
  { value: "other", label: "Other" },
] as const;