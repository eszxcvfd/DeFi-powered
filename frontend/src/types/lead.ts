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
};

export type LeadActivity = {
  id: string;
  kind: string;
  actor: string;
  body: string;
  from_stage: string;
  to_stage: string;
  created_at: string;
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