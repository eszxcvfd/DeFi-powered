import type { DashboardOverview } from "@/types/dashboard";

export type DashboardQuery = {
  start?: string;
  end?: string;
  preset?: "last_7_days" | "last_30_days" | "this_month";
};

export async function getDashboardOverview(params: DashboardQuery = {}): Promise<DashboardOverview> {
  const sp = new URLSearchParams();
  if (params.preset) sp.set("preset", params.preset);
  if (params.start) sp.set("start", params.start);
  if (params.end) sp.set("end", params.end);
  const q = sp.toString();
  const r = await fetch(`/reporting/dashboard-overview${q ? `?${q}` : ""}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "dashboard overview failed");
  }
  return r.json();
}