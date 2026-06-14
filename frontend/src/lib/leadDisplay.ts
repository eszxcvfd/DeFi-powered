import type { LeadSummary } from "@/types/lead";

/** Primary label for tables/Kanban: event title when linked, else display name. */
export function leadPrimaryLabel(lead: LeadSummary): string {
  const event = (lead.event_title || "").trim();
  if (event) return event.length > 72 ? `${event.slice(0, 69)}…` : event;
  return lead.display_name;
}

export function leadSecondaryLine(lead: LeadSummary): string {
  const parts: string[] = [];
  if (lead.company?.trim()) parts.push(lead.company.trim());
  if (lead.region?.trim()) parts.push(lead.region.trim());
  if (lead.title?.trim() && !parts.includes(lead.title.trim())) parts.push(lead.title.trim());
  return parts.join(" · ") || lead.display_name;
}