export type NotificationType =
  | "job_completed"
  | "job_needs_user_action"
  | "job_failed"
  | "reminder_due"
  | "reminder_overdue"
  | "event_upcoming";

export type NotificationState = "unread" | "read" | "dismissed";

export interface NotificationView {
  id: string;
  organization_id: string;
  user_id: string;
  notification_type: NotificationType;
  state: NotificationState;
  source_record_type: string;
  source_record_id: string;
  title: string;
  summary: string;
  deep_link: string;
  created_at: string;
  read_at: string | null;
  dismissed_at: string | null;
}

export interface InboxResponse {
  items: NotificationView[];
  unread_count: number;
  total: number;
}

export interface NotificationPreference {
  notification_type: NotificationType;
  in_app_enabled: boolean;
  email_enabled: boolean;
  updated_at: string;
}

export interface PreferencesResponse {
  preferences: NotificationPreference[];
  is_seeded: boolean;
}

export interface ScanResponse {
  candidates: number;
  in_app_created: number;
  emails_attempted: number;
  emails_suppressed: number;
  emails_failed: number;
}
