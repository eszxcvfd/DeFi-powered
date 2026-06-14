import { LEAD_STAGE_LABELS, OUTCOME_TYPE_LABELS } from "@/types/lead";
import type { LeadActivity } from "@/types/lead";

export function formatLeadActivityLine(a: LeadActivity): string {
  if (a.kind === "outcome_recorded" && a.outcome_type) {
    const label = OUTCOME_TYPE_LABELS[a.outcome_type] ?? a.outcome_type;
    const when = a.occurred_at || a.created_at;
    let line = `Outcome: ${label}`;
    const generic = /^Recorded \w+ outcome$/i.test(a.body.trim());
    if (a.body && !generic) {
      line += ` — ${a.body}`;
    }
    try {
      line += ` · ${new Date(when).toLocaleString()}`;
    } catch {
      /* ignore */
    }
    line += ` (${a.actor})`;
    return line;
  }
  if (a.kind === "stage_changed") {
    const from = LEAD_STAGE_LABELS[a.from_stage] ?? a.from_stage;
    const to = LEAD_STAGE_LABELS[a.to_stage] ?? a.to_stage;
    return `Stage: ${from} → ${to} (${a.actor})`;
  }
  if (a.kind === "note_added" || a.body) {
    return `Note: ${a.body || "—"} (${a.actor})`;
  }
  return `${a.kind}${a.body ? ` — ${a.body}` : ""} (${a.actor})`;
}

export function latestOutcomeBadgeText(outcomeType: string): string {
  return OUTCOME_TYPE_LABELS[outcomeType] ?? outcomeType;
}