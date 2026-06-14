import type { FunnelReport } from "@/types/funnel";

export type FunnelQuery = {
  start?: string;
  end?: string;
  preset?: "last_7_days" | "last_30_days" | "this_month";
};

export async function getFunnelReport(params: FunnelQuery = {}): Promise<FunnelReport> {
  const sp = new URLSearchParams();
  if (params.preset) sp.set("preset", params.preset);
  if (params.start) sp.set("start", params.start);
  if (params.end) sp.set("end", params.end);
  const q = sp.toString();
  const r = await fetch(`/reports/funnel${q ? `?${q}` : ""}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "funnel report failed");
  }
  return r.json();
}