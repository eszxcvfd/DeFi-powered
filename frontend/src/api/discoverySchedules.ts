import type { DiscoverySchedule } from "@/types/discoverySchedule";

export async function listDiscoverySchedules(campaignId: string): Promise<DiscoverySchedule[]> {
  const r = await fetch(`/campaigns/${campaignId}/discovery-schedules`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<DiscoverySchedule[]>;
}

export async function createDiscoverySchedule(
  campaignId: string,
  body: { recurrence: Record<string, unknown>; source_ids?: string[] }
): Promise<DiscoverySchedule> {
  const r = await fetch(`/campaigns/${campaignId}/discovery-schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<DiscoverySchedule>;
}

export async function patchDiscoverySchedule(
  scheduleId: string,
  body: { enabled_state?: string; recurrence?: Record<string, unknown> }
): Promise<DiscoverySchedule> {
  const r = await fetch(`/discovery-schedules/${scheduleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<DiscoverySchedule>;
}