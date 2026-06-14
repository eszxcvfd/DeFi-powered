import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getFunnelReport } from "@/api/funnel";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import type { FunnelReport } from "@/types/funnel";
import { ReportExportControls } from "@/components/ReportExportControls";
import { CalendarRange, Loader2 } from "lucide-react";

type Preset = "last_7_days" | "last_30_days" | "this_month";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "last_7_days", label: "Last 7 days" },
  { key: "last_30_days", label: "Last 30 days" },
  { key: "this_month", label: "This month" },
];

export default function FunnelReportPage() {
  const [preset, setPreset] = useState<Preset>("last_30_days");
  const [data, setData] = useState<FunnelReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (p: Preset) => {
    setLoading(true);
    setError(null);
    try {
      setData(await getFunnelReport({ preset: p }));
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

  const maxCount = data ? Math.max(1, ...data.steps.map((s) => s.count)) : 1;

  return (
    <AppPageShell testId="funnel-report">
      <AppPageHeader
        title="Conversion funnel"
        subtitle={
          <>
            Event → lead → contact → response → meeting → opportunity.{" "}
            <Link to="/" className="underline font-medium">
              Dashboard
            </Link>
            {" · "}
            <Link to="/reports/source-performance" className="underline font-medium">
              Source performance
            </Link>
          </>
        }
        actions={
          <div className="flex flex-col items-end gap-2">
            <ReportExportControls reportType="funnel" preset={preset} testIdPrefix="funnel" />
            <div className="flex items-center gap-2 flex-wrap" data-testid="funnel-range-controls">
              <CalendarRange className="size-4 text-slate-400" strokeWidth={1.5} />
              {PRESETS.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant={preset === key ? "default" : "ghost"}
                  className="rounded-sm text-xs h-8"
                  data-testid={`funnel-preset-${key}`}
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
          <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg" data-testid="funnel-error">
            {error}
          </p>
        )}

        {data && (
          <>
            <p className="text-[11px] font-mono text-slate-500 mb-2" data-testid="funnel-window-label">
              {data.cohort.start} → {data.cohort.end}
              {data.cohort.preset ? ` (${data.cohort.preset})` : ""}
            </p>
            <p
              className="text-[11px] text-slate-600 mb-4 border border-slate-200 bg-white p-3 rounded-lg"
              data-testid="funnel-cohort-rule"
            >
              {data.cohort.rule}
            </p>
            {data.unattributed && (
              <p
                className="text-xs text-amber-900 bg-amber-50 border border-amber-200 p-3 rounded-lg mb-4"
                data-testid="funnel-unattributed"
              >
                {data.unattributed.explanation} ({data.unattributed.manual_leads_in_cohort} in cohort)
              </p>
            )}
            <p className="text-[11px] text-slate-500 mb-4" data-testid="funnel-freshness">
              {data.freshness.last_updated_at
                ? `Data through ${new Date(data.freshness.last_updated_at).toLocaleString()}`
                : "No matching records in this cohort"}
            </p>
          </>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Loading funnel…
          </div>
        )}

        {!loading && data && (
          <AppSection title="Steps">
            <ol className="space-y-4" data-testid="funnel-steps">
              {data.steps.map((step, index) => (
                <li
                  key={step.key}
                  className="border border-slate-100 rounded-md p-4 bg-slate-50/50"
                  data-testid={`funnel-step-${step.key}`}
                >
                  <div className="flex items-center justify-between gap-4 mb-2">
                    <span className="text-xs font-mono text-slate-400">{index + 1}</span>
                    <span className="text-sm font-semibold text-slate-900 flex-1">{step.label}</span>
                    <span
                      className="text-2xl font-bold tabular-nums text-slate-900"
                      data-testid={`funnel-step-count-${step.key}`}
                    >
                      {step.count}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-sm overflow-hidden">
                    <div
                      className="h-full bg-slate-700 transition-all"
                      style={{ width: `${Math.round((step.count / maxCount) * 100)}%` }}
                    />
                  </div>
                  {step.note && <p className="text-[11px] text-slate-500 mt-2">{step.note}</p>}
                  {step.count === 0 && !step.note && (
                    <p className="text-[11px] text-slate-400 mt-2" data-testid={`funnel-step-empty-${step.key}`}>
                      No records in cohort
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </AppSection>
        )}
      </div>
    </AppPageShell>
  );
}