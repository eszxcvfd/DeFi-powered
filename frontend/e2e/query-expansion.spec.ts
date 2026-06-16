import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";

test("generate, approve query expansion, run discovery with snapshot", async ({ page, request }) => {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const create = await request.post(`${API}/admin/connectors`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: "E2E QE Source",
      domain: `e2e-qe-${Date.now()}.local`,
      connector_type: "rss",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", valid: true, quota_per_day: 500, quota_used_today: 0 },
    },
  });
  expect(create.ok()).toBeTruthy();
  const conn = await create.json();

  const camp = await request.post(`${API}/campaigns`, {
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
    data: {
      name: `QE Camp ${Date.now()}`,
      target_industry: "Tech",
      positive_keywords: ["artificial intelligence summit"],
    },
  });
  expect(camp.ok()).toBeTruthy();
  const campaignId = (await camp.json()).id as string;

  await page.goto(`/campaigns/${campaignId}`);
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  const pin = await request.put(`${API}/campaigns/${campaignId}/sources`, {
    data: { source_ids: [conn.id] },
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
  });
  expect(pin.ok()).toBeTruthy();

  await page.getByTestId("query-expansion-generate").click();
  await expect(page.getByTestId("query-expansion-variants")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("query-expansion-status")).toContainText(/review required/i);

  await page.getByTestId("query-expansion-approve").click();
  await expect(page.getByTestId("query-expansion-status")).toContainText(/approved/i, { timeout: 10_000 });

  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-progress")).toBeVisible({ timeout: 20_000 });
});