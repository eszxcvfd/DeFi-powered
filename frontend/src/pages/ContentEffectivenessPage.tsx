import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getContentEffectivenessReport } from "@/api/contentEffectiveness";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { Button } from "@/components/ui/button";
import type { ContentEffectivenessGrouping, ContentEffectivenessReport } from "@/types/contentEffectiveness";
import { ReportExportControls } from "@/components/ReportExportControls";
import { CalendarRange, Loader2 } from "lucide-react";

type Preset = "last_7_days" | "last_30_days" | "this_month";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "last_7_days", label: "Last 7 days" },
  { key: "last_30_days", label: "Last 30 days" },
  { key: "this_month", label: "This month" },
];

const GROUPINGS: { key: ContentEffectivenessGrouping; label: string }[] = [
  { key: "content_type", label: "Content type" },
  { key: "tone", label: "Tone" },
  { key: "template", label: "Template" },
];

export default function ContentEffectivenessPage() {
  const [preset, setPreset] = useState<Preset>("last_30_days");
  const [grouping, setGrouping] = useState<ContentEffectivenessGrouping>("content_type");
  const [data, setData] = useState<ContentEffectivenessReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rowsPage, setRowsPage] = useState(1);

  const load = useCallback(async (p: Preset, g: ContentEffectivenessGrouping) => {
    setLoading(true);
    setError(null);
    try {
      setData(await getContentEffectivenessReport({ preset: p, grouping: g }));
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
    <AppPageShell testId="content-effectiveness-report">
      <AppPageHeader
        title="Content effectiveness"
        subtitle={
          <>
            Used content vs linked outcomes.{" "}
            <Link to="/reports/source-performance" className="underline font-medium">
              Source performance
            </Link>
            {" · "}
            <Link to="/reports/funnel" className="underline font-medium">
              Funnel
            </Link>
          </>
        }
        actions={
          <div className="flex flex-col items-end gap-2">
            <ReportExportControls
              reportType="content_effectiveness"
              preset={preset}
              grouping={grouping}
              testIdPrefix="content-effectiveness"
            />
            <div className="flex items-center gap-2 flex-wrap" data-testid="content-effectiveness-range-controls">
              <CalendarRange className="size-4 text-slate-400" strokeWidth={1.5} />
              {PRESETS.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant={preset === key ? "default" : "ghost"}
                  className="rounded-sm text-xs h-8"
                  data-testid={`content-effectiveness-preset-${key}`}
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
        <div className="flex flex-wrap gap-2 mb-4" data-testid="content-effectiveness-grouping-controls">
          {GROUPINGS.map(({ key, label }) => (
            <Button
              key={key}
              type="button"
              variant={grouping === key ? "default" : "ghost"}
              className="rounded-sm text-xs h-8"
              data-testid={`content-effectiveness-grouping-${key}`}
              onClick={() => setGrouping(key)}
            >
              {label}
            </Button>
          ))}
        </div>

        {data && (
          <p
            className="text-[11px] text-slate-600 mb-4 border border-slate-200 bg-white p-3 rounded-lg"
            data-testid="content-effectiveness-correlation-note"
          >
            {data.correlation_note}
          </p>
        )}

        {error && (
          <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg" data-testid="content-effectiveness-error">
            {error}
          </p>
        )}

        {data && (
          <>
            <p className="text-[11px] font-mono text-slate-500 mb-2" data-testid="content-effectiveness-window-label">
              {data.window.start} → {data.window.end}
              {data.window.preset ? ` (${data.window.preset})` : ""} · {data.grouping_label}
            </p>
            {data.unattributed && (
              <p
                className="text-xs text-amber-900 bg-amber-50 border border-amber-200 p-3 rounded-lg mb-4"
                data-testid="content-effectiveness-unattributed"
              >
                {data.unattributed.explanation}
                {data.unattributed.used_content_without_metadata > 0 &&
                  ` Used without metadata: ${data.unattributed.used_content_without_metadata}.`}
                {data.unattributed.outcomes_without_content_link > 0 &&
                  ` Outcomes without link: ${data.unattributed.outcomes_without_content_link}.`}
              </p>
            )}
            <p className="text-[11px] text-slate-500 mb-4" data-testid="content-effectiveness-freshness">
              {data.freshness.last_updated_at
                ? `Data through ${new Date(data.freshness.last_updated_at).toLocaleString()}`
                : "No matching records in this window"}
            </p>
          </>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Loading content effectiveness…
          </div>
        )}

        {!loading && data && data.rows.length === 0 && (
          <p className="text-sm text-slate-500 border border-dashed border-slate-200 p-6 rounded-lg" data-testid="content-effectiveness-empty">
            No grouped rows. Mark content as used and link outcomes to drafts to populate this report.
          </p>
        )}

        {!loading && data && data.rows.length > 0 && (
          <AppSection title="Results">
            <div className="overflow-x-auto -mx-4 sm:mx-0" data-testid="content-effectiveness-table">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs text-slate-600">
                  <tr>
                    <th className="p-3 font-medium">Group</th>
                    <th className="p-3 font-medium tabular-nums">Used</th>
                    <th className="p-3 font-medium tabular-nums">Linked outcomes</th>
                    <th className="p-3 font-medium tabular-nums">Contact</th>
                    <th className="p-3 font-medium tabular-nums">Response</th>
                    <th className="p-3 font-medium tabular-nums">Meeting</th>
                    <th className="p-3 font-medium tabular-nums">Opportunity</th>
                  </tr>
                </thead>
                <tbody>
                  {paginateSlice(data.rows, rowsPage).map((row) => (
                    <tr
                      key={row.group_key}
                      className="border-t border-slate-100"
                      data-testid={`content-effectiveness-row-${row.group_key}`}
                    >
                      <td className="p-3 font-medium text-slate-900">{row.group_label}</td>
                      <td className="p-3 tabular-nums">{row.metrics.content_used}</td>
                      <td className="p-3 tabular-nums">{row.metrics.outcomes_linked}</td>
                      <td className="p-3 tabular-nums">{row.metrics.outcomes_contact}</td>
                      <td className="p-3 tabular-nums">{row.metrics.outcomes_response}</td>
                      <td className="p-3 tabular-nums">{row.metrics.outcomes_meeting}</td>
                      <td className="p-3 tabular-nums">{row.metrics.outcomes_opportunity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ListPagination
              page={rowsPage}
              totalItems={data.rows.length}
              onPageChange={setRowsPage}
              testId="content-effectiveness-pagination"
            />
          </AppSection>
        )}
      </div>
    </AppPageShell>
  );
}