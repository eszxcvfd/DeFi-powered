import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSourcePerformanceReport } from "@/api/sourcePerformance";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { Button } from "@/components/ui/button";
import type { SourcePerformanceGrouping, SourcePerformanceReport } from "@/types/sourcePerformance";
import { ReportExportControls } from "@/components/ReportExportControls";
import { CalendarRange, Loader2 } from "lucide-react";

type Preset = "last_7_days" | "last_30_days" | "this_month";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "last_7_days", label: "Last 7 days" },
  { key: "last_30_days", label: "Last 30 days" },
  { key: "this_month", label: "This month" },
];

const GROUPINGS: { key: SourcePerformanceGrouping; label: string }[] = [
  { key: "campaign", label: "Campaign" },
  { key: "industry", label: "Industry" },
  { key: "platform", label: "Platform" },
  { key: "connector", label: "Connector" },
];

export default function SourcePerformancePage() {
  const [preset, setPreset] = useState<Preset>("last_30_days");
  const [grouping, setGrouping] = useState<SourcePerformanceGrouping>("campaign");
  const [data, setData] = useState<SourcePerformanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rowsPage, setRowsPage] = useState(1);

  const load = useCallback(async (p: Preset, g: SourcePerformanceGrouping) => {
    setLoading(true);
    setError(null);
    try {
      setData(await getSourcePerformanceReport({ preset: p, grouping: g }));
    } catch (e) {
      setData(null);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(preset, grouping);
  }, [preset, grouping, load]);

  useEffect(() => {
    setRowsPage(1);
  }, [preset, grouping]);

  return (
    <AppPageShell testId="source-performance-report">
      <AppPageHeader
        title="Source performance"
        subtitle={
          <>
            Grouped pipeline metrics.{" "}
            <Link to="/reports/funnel" className="underline font-medium">
              Funnel
            </Link>
            {" · "}
            <Link to="/reports/content-effectiveness" className="underline font-medium">
              Content
            </Link>
            {" · "}
            <Link to="/" className="underline font-medium">
              Dashboard
            </Link>
          </>
        }
        actions={
          <div className="flex flex-col items-end gap-2">
            <ReportExportControls
              reportType="source_performance"
              preset={preset}
              grouping={grouping}
              testIdPrefix="source-performance"
            />
            <div className="flex items-center gap-2 flex-wrap" data-testid="source-performance-range-controls">
              <CalendarRange className="size-4 text-slate-400" strokeWidth={1.5} />
              {PRESETS.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant={preset === key ? "default" : "ghost"}
                  className="rounded-sm text-xs h-8"
                  data-testid={`source-performance-preset-${key}`}
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
        <div className="flex flex-wrap gap-2 mb-6" data-testid="source-performance-grouping-controls">
          {GROUPINGS.map(({ key, label }) => (
            <Button
              key={key}
              type="button"
              variant={grouping === key ? "default" : "ghost"}
              className="rounded-sm text-xs h-8"
              data-testid={`source-performance-grouping-${key}`}
              onClick={() => setGrouping(key)}
            >
              {label}
            </Button>
          ))}
        </div>

        {error && (
          <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg" data-testid="source-performance-error">
            {error}
          </p>
        )}

        {data && (
          <>
            <p className="text-[11px] font-mono text-slate-500 mb-2" data-testid="source-performance-window-label">
              {data.window.start} → {data.window.end}
              {data.window.preset ? ` (${data.window.preset})` : ""} · {data.grouping_label}
            </p>
            {data.unattributed && (
              <p
                className="text-xs text-amber-900 bg-amber-50 border border-amber-200 p-3 rounded-lg mb-4"
                data-testid="source-performance-unattributed"
              >
                {data.unattributed.explanation}
                {data.unattributed.events_without_source_link > 0 &&
                  ` Events without source link: ${data.unattributed.events_without_source_link}.`}
                {data.unattributed.leads_without_group_key > 0 &&
                  ` Leads outside grouping: ${data.unattributed.leads_without_group_key}.`}
              </p>
            )}
            <p className="text-[11px] text-slate-500 mb-4" data-testid="source-performance-freshness">
              {data.freshness.last_updated_at
                ? `Data through ${new Date(data.freshness.last_updated_at).toLocaleString()}`
                : "No matching records in this window"}
            </p>
          </>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Loading source performance…
          </div>
        )}

        {!loading && data && data.rows.length === 0 && (
          <p className="text-sm text-slate-500 border border-dashed border-slate-200 p-6 rounded-lg" data-testid="source-performance-empty">
            No grouped rows for this window and grouping.
          </p>
        )}

        {!loading && data && data.rows.length > 0 && (
          <AppSection title="Results">
            <div className="overflow-x-auto -mx-4 sm:mx-0" data-testid="source-performance-table">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs text-slate-600">
                  <tr>
                    <th className="p-3 font-medium">Group</th>
                    <th className="p-3 font-medium tabular-nums">Events</th>
                    <th className="p-3 font-medium tabular-nums">Prioritized</th>
                    <th className="p-3 font-medium tabular-nums">Leads</th>
                    <th className="p-3 font-medium tabular-nums">Opportunities</th>
                  </tr>
                </thead>
                <tbody>
                  {paginateSlice(data.rows, rowsPage).map((row) => (
                    <tr
                      key={row.group_key}
                      className="border-t border-slate-100"
                      data-testid={`source-performance-row-${row.group_key}`}
                    >
                      <td className="p-3 font-medium text-slate-900">{row.group_label}</td>
                      <td className="p-3 tabular-nums">{row.metrics.events_discovered}</td>
                      <td className="p-3 tabular-nums">{row.metrics.events_prioritized}</td>
                      <td className="p-3 tabular-nums">{row.metrics.leads_created}</td>
                      <td className="p-3 tabular-nums">{row.metrics.opportunities}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ListPagination
              page={rowsPage}
              totalItems={data.rows.length}
              onPageChange={setRowsPage}
              testId="source-performance-pagination"
            />
          </AppSection>
        )}
      </div>
    </AppPageShell>
  );
}