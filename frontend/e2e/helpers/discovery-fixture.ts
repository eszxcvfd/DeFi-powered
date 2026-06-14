import { expect, type Page } from "@playwright/test";

const SUCCESS_MOCK_DOMAIN = "success-mock.example.com";

/** Registers a deterministic mock connector (always succeeds under LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS). */
export async function ensureSuccessMockConnector(page: Page): Promise<void> {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });
  await page.goto("/admin/connectors");
  await page.getByTestId("connector-name").fill("Browser E2E Mock");
  await page.getByTestId("connector-domain").fill(SUCCESS_MOCK_DOMAIN);
  await page.getByTestId("connector-add").click();
}

export async function pinCampaignToSuccessMockSource(page: Page, campaignId: string): Promise<void> {
  const sourceId = await page.evaluate(async (domain) => {
    const r = await fetch("/campaigns/runnable-sources");
    if (!r.ok) throw new Error(`runnable-sources ${r.status}`);
    const sources = (await r.json()) as { id: string; domain: string }[];
    const hit = sources.find((s) => s.domain === domain);
    if (!hit) throw new Error(`no runnable source for ${domain}`);
    return hit.id;
  }, SUCCESS_MOCK_DOMAIN);

  const ok = await page.evaluate(
    async ({ cid, sid }) => {
      const r = await fetch(`/campaigns/${cid}/sources`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_ids: [sid] }),
      });
      return r.ok;
    },
    { cid: campaignId, sid: sourceId },
  );
  expect(ok).toBe(true);
}

export async function runDiscoveryUntilTerminal(
  page: Page,
  options?: { expectSuccess?: boolean },
): Promise<void> {
  const expectSuccess = options?.expectSuccess ?? true;
  await page.getByTestId("run-discovery").click();
  if (expectSuccess) {
    await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial/, {
      timeout: 60_000,
    });
  } else {
    await expect(page.getByTestId("discovery-status")).toHaveText(
      /succeeded|partial|failed|cancelled|needs_user_action/,
      { timeout: 60_000 },
    );
  }
}