import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboardOverview } from "@/api/dashboard";
import { Button } from "@/components/ui/button";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import type { DashboardMetricCard, DashboardOverview } from "@/types/dashboard";
import { ReportExportControls } from "@/components/ReportExportControls";
import { Loader2, CalendarRange } from "lucide-react";

type Preset = "last_7_days" | "last_30_days" | "this_month";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "last_7_days", label: "Last 7 days" },
  { key: "last_30_days", label: "Last 30 days" },
  { key: "this_month", label: "This month" },
];

function formatFreshness(card: DashboardMetricCard): string {
  const at = card.freshness.last_updated_at;
  if (!at) {
    if (card.availability === "unavailable") return "No source data yet";
    return "No updates in range";
  }
  try {
    return `Updated ${new Date(at).toLocaleString()}`;
  } catch {
    return "Updated recently";
  }
}

function MetricValue({ card }: { card: DashboardMetricCard }) {
  if (card.availability === "unavailable") {
    return (
      <p className="text-sm text-slate-500 mt-2" data-testid={`widget-${card.key}-unavailable`}>
        Unavailable
      </p>
    );
  }
  return (
    <p className="text-3xl font-bold text-slate-900 mt-2 tabular-nums" data-testid={`widget-${card.key}-value`}>
      {card.value ?? 0}
    </p>
  );
}

export default function DashboardOverviewPage() {
  const [preset, setPreset] = useState<Preset>("last_30_days");
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (p: Preset) => {
    setLoading(true);
    setError(null);
    try {
      const overview = await getDashboardOverview({ preset: p });
      setData(overview);
    } catch (e) {
      setData(null);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(preset);
  }, [preset, load]);

  return (
    <AppPageShell testId="dashboard-overview">
      <AppPageHeader
        title="Dashboard"
        subtitle={
          <>
            Summary metrics for the selected range.{" "}
            <Link to="/reports/funnel" className="underline font-medium" data-testid="dashboard-link-funnel">
              Funnel
            </Link>
            {" · "}
            <Link
              to="/reports/source-performance"
              className="underline font-medium"
              data-testid="dashboard-link-source-performance"
            >
              Source performance
            </Link>
          </>
        }
        actions={
          <div className="flex flex-col items-end gap-2">
            <ReportExportControls reportType="dashboard" preset={preset} testIdPrefix="dashboard" />
            <div className="flex items-center gap-2 flex-wrap" data-testid="dashboard-range-controls">
              <CalendarRange className="size-4 text-slate-400" strokeWidth={1.5} />
              {PRESETS.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant={preset === key ? "default" : "ghost"}
                  className="rounded-sm text-xs h-8"
                  data-testid={`dashboard-preset-${key}`}
                  onClick={() => setPreset(key)}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        {error && (
          <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg" data-testid="dashboard-error">
            {error}
          </p>
        )}

        {data && (
          <p className="text-[11px] font-mono text-slate-500 mb-4" data-testid="dashboard-window-label">
            Window: {data.time_window.start} → {data.time_window.end}
            {data.time_window.preset ? ` (${data.time_window.preset})` : ""}
          </p>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Loading overview…
          </div>
        )}

        {!loading && data && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.widgets.map((card) => (
              <AppSection
                key={card.key}
                title={card.label}
                testId={`dashboard-widget-${card.key}`}
                className="!overflow-visible"
              >
                <MetricValue card={card} />
                <p className="text-[11px] text-slate-500 mt-3" data-testid={`widget-${card.key}-freshness`}>
                  {formatFreshness(card)}
                </p>
                {card.availability === "unavailable" && card.unavailable_reason && (
                  <p className="text-[11px] text-amber-800 mt-1">{card.unavailable_reason}</p>
                )}
                {card.availability === "empty" && (
                  <p className="text-[11px] text-slate-400 mt-1" data-testid={`widget-${card.key}-empty`}>
                    No records in this range
                  </p>
                )}
              </AppSection>
            ))}
          </div>
        )}
      </div>
    </AppPageShell>
  );
}