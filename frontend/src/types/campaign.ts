export type IcpCriteria = {
  industry: string;
  organization_type: string;
  company_size: string;
  role_or_title_targets: string[];
  country_or_region: string;
  pain_points: string[];
  use_cases: string[];
  positive_keywords: string[];
  excluded_keywords: string[];
};

export type CampaignSummary = {
  id: string;
  name: string;
  target_industry: string;
  status: string;
  updated_at: string;
  parent_campaign_id: string | null;
  parent_name: string | null;
  created_by_actor: string;
  creation_source: string;
  creation_source_label: string;
  automation_run_id: string | null;
  child_count: number;
  depth: number;
};

export type CampaignDetail = CampaignSummary & {
  organization_id: string;
  description: string;
  product_or_service_focus: string;
  market_regions: string[];
  languages: string[];
  timezone: string;
  date_range: { start: string | null; end: string | null };
  positive_keywords: string[];
  exclude_keywords: string[];
  icp: IcpCriteria;
  scoring_weights: Record<string, number>;
  created_at: string;
  deferred: Record<string, string>;
};

export type CampaignCreatePayload = {
  name: string;
  description: string;
  target_industry: string;
  product_or_service_focus: string;
  market_regions: string[];
  languages: string[];
  timezone: string;
  date_range: { start: string | null; end: string | null };
  positive_keywords: string[];
  exclude_keywords: string[];
  icp: IcpCriteria;
  scoring_weights: Record<string, number>;
};