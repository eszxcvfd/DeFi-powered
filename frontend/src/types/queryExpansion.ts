export type QueryExpansionVariant = {
  text: string;
  variant_type: string;
  source: string;
  confidence?: number | null;
  assumption?: string | null;
  user_edited?: boolean;
  removed?: boolean;
};

export type QueryExpansionSet = {
  id: string;
  campaign_id: string;
  status: string;
  generation_mode: string;
  version: number;
  requires_review: boolean;
  grouped_variants: Record<string, QueryExpansionVariant[]>;
  approved_at: string | null;
};