export type DashboardTimeWindow = {
  start: string;
  end: string;
  preset: string | null;
};

export type WidgetFreshness = {
  last_updated_at: string | null;
  source: string;
};

export type DashboardMetricCard = {
  key: string;
  label: string;
  availability: "available" | "empty" | "unavailable";
  value: number | null;
  freshness: WidgetFreshness;
  unavailable_reason: string | null;
};

export type DashboardOverview = {
  time_window: DashboardTimeWindow;
  widgets: DashboardMetricCard[];
  generated_at: string;
};