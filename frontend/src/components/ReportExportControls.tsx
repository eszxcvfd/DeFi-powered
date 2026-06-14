import { useState } from "react";
import { downloadReportExport, type ReportExportQuery, type ReportExportType } from "@/api/reportExport";
import { Button } from "@/components/ui/button";
import { Download, Loader2 } from "lucide-react";

type Props = {
  reportType: ReportExportType;
  preset?: ReportExportQuery["preset"];
  grouping?: string;
  testIdPrefix: string;
};

export function ReportExportControls({ reportType, preset, grouping, testIdPrefix }: Props) {
  const [busy, setBusy] = useState<"csv" | "printable" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(format: "csv" | "printable") {
    setBusy(format);
    setError(null);
    setMessage(null);
    try {
      await downloadReportExport({
        report_type: reportType,
        format,
        preset,
        grouping,
      });
      setMessage(format === "csv" ? "CSV download started." : "Printable download started.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid={`${testIdPrefix}-export-controls`}
    >
      <Download className="size-4 text-slate-400" strokeWidth={1.5} />
      <Button
        type="button"
        variant="ghost"
        className="rounded-sm text-xs h-8 border border-slate-200"
        disabled={busy !== null}
        data-testid={`${testIdPrefix}-export-csv`}
        onClick={() => run("csv")}
      >
        {busy === "csv" ? <Loader2 className="size-3 animate-spin" /> : null}
        Export CSV
      </Button>
      <Button
        type="button"
        variant="ghost"
        className="rounded-sm text-xs h-8 border border-slate-200"
        disabled={busy !== null}
        data-testid={`${testIdPrefix}-export-printable`}
        onClick={() => run("printable")}
      >
        {busy === "printable" ? <Loader2 className="size-3 animate-spin" /> : null}
        Export printable
      </Button>
      {message && (
        <span className="text-[11px] text-emerald-700" data-testid={`${testIdPrefix}-export-success`}>
          {message}
        </span>
      )}
      {error && (
        <span className="text-[11px] text-red-600" data-testid={`${testIdPrefix}-export-error`}>
          {error}
        </span>
      )}
    </div>
  );
}