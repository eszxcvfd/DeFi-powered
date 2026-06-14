import type { SourcePerformanceGrouping, SourcePerformanceReport } from "@/types/sourcePerformance";

type Query = {
  preset?: string;
  start?: string;
  end?: string;
  grouping?: SourcePerformanceGrouping;
};

export async function getSourcePerformanceReport(params: Query = {}): Promise<SourcePerformanceReport> {
  const q = new URLSearchParams();
  if (params.preset) q.set("preset", params.preset);
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  if (params.grouping) q.set("grouping", params.grouping);
  const r = await fetch(`/reports/source-performance${q.toString() ? `?${q}` : ""}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "source performance report failed");
  }
  return r.json();
}