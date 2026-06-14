export type RunnableSource = {
  id: string;
  name: string;
  domain: string;
  connector_type: string;
  runnable: boolean;
  denied_reasons: string[];
  preferred_over_browser: boolean;
};

export type ConnectorView = {
  id: string;
  name: string;
  domain: string;
  connector_type: string;
  automation_engine: string;
  authentication_mode: string;
  enabled: boolean;
  approved: boolean;
  approved_by: string | null;
  policy_state: string;
  runnable: boolean;
  denied_reasons: string[];
  has_secret: boolean;
  secret_display: string;
  preferred_over_browser: boolean;
};