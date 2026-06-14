export type ReportExportType =
  | "dashboard"
  | "funnel"
  | "source_performance"
  | "content_effectiveness";

export type ReportExportFormat = "csv" | "printable";

export type ReportExportQuery = {
  report_type: ReportExportType;
  format: ReportExportFormat;
  preset?: "last_7_days" | "last_30_days" | "this_month";
  start?: string;
  end?: string;
  grouping?: string;
};

export async function downloadReportExport(params: ReportExportQuery): Promise<void> {
  const sp = new URLSearchParams();
  sp.set("report_type", params.report_type);
  sp.set("format", params.format);
  if (params.preset) sp.set("preset", params.preset);
  if (params.start) sp.set("start", params.start);
  if (params.end) sp.set("end", params.end);
  if (params.grouping) sp.set("grouping", params.grouping);

  const r = await fetch(`/reports/export?${sp.toString()}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "report export failed");
  }
  const blob = await r.blob();
  const disposition = r.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? `report-export.${params.format === "csv" ? "csv" : "html"}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}