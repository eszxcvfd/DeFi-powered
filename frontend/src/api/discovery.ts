import type { DiscoveryJob } from "@/types/discovery";

export async function startDiscovery(
  campaignId: string,
  options?: { use_expansion?: boolean },
): Promise<DiscoveryJob> {
  const r = await fetch(`/campaigns/${campaignId}/discovery-jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_expansion: options?.use_expansion ?? true }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getDiscoveryJob(jobId: string): Promise<DiscoveryJob> {
  const r = await fetch(`/discovery-jobs/${jobId}`);
  if (!r.ok) throw new Error("get job failed");
  return r.json();
}

export async function cancelDiscoveryJob(jobId: string): Promise<DiscoveryJob> {
  const r = await fetch(`/discovery-jobs/${jobId}/cancel`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}