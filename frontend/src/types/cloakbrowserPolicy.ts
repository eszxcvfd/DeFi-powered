export type CloakBrowserPolicyView = {
  source_id: string;
  source_name: string;
  automation_engine: string;
  policy_state: string;
  purpose_rationale: string;
  owner_admin_approved: boolean;
  compliance_approved: boolean;
  runtime_status: string;
  kill_switch_active: boolean;
  cloakbrowser_launch_allowed: boolean;
  blocked_reasons: string[];
  pinned_version: string | null;
};