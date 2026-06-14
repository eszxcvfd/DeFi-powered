import type { ContentEffectivenessGrouping, ContentEffectivenessReport } from "@/types/contentEffectiveness";

type Query = {
  preset?: string;
  start?: string;
  end?: string;
  grouping?: ContentEffectivenessGrouping;
};

export async function getContentEffectivenessReport(
  params: Query = {}
): Promise<ContentEffectivenessReport> {
  const q = new URLSearchParams();
  if (params.preset) q.set("preset", params.preset);
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  if (params.grouping) q.set("grouping", params.grouping);
  const r = await fetch(`/reports/content-effectiveness${q.toString() ? `?${q}` : ""}`);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "content effectiveness report failed");
  }
  return r.json();
}