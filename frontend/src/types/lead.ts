export type LeadReminderSummary = {
  has_reminder: boolean;
  state: string | null;
  due_date: string | null;
  reminder_id: string | null;
};

export type LeadSummary = {
  id: string;
  display_name: string;
  company: string;
  title: string;
  owner: string;
  stage: string;
  discovery_source: string;
  campaign_id: string | null;
  event_id: string | null;
  follow_up_date: string | null;
  updated_at: string;
  reminder: LeadReminderSummary;
  event_title?: string;
  region?: string;
  latest_outcome?: LatestLeadOutcome | null;
};

export type LatestLeadOutcome = {
  outcome_type: string;
  occurred_at: string;
  actor: string;
  activity_id: string;
  linked_content_draft_id: string | null;
  notes: string;
};

export type LeadActivity = {
  id: string;
  kind: string;
  actor: string;
  body: string;
  from_stage: string;
  to_stage: string;
  created_at: string;
  outcome_type?: string;
  occurred_at?: string | null;
  linked_content_draft_id?: string | null;
};

export type LeadDetail = LeadSummary & {
  public_url: string;
  interests: string;
  pain_points: string;
  lawful_basis_note: string;
  notes: string;
  manual_entry_note: string;
  origin_kind: string;
  created_by: string;
  created_at: string;
  recent_activity: LeadActivity[];
};

export const LEAD_STAGE_LABELS: Record<string, string> = {
  newly_discovered: "Newly discovered",
  watched: "Watched",
  connected: "Connected",
  message_sent: "Message sent",
  responded: "Responded",
  meeting_scheduled: "Meeting scheduled",
  in_discussion: "In discussion",
  opportunity: "Opportunity",
  not_fit: "Not fit",
};

export const OUTCOME_TYPE_LABELS: Record<string, string> = {
  contact: "Contact",
  response: "Response",
  meeting: "Meeting",
  opportunity: "Opportunity",
};