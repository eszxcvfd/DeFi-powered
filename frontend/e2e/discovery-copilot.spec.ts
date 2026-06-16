import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";

test("ask discovery copilot and accept into query expansion", async ({ page, request }) => {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const create = await request.post(`${API}/admin/connectors`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: "E2E Copilot Source",
      domain: `e2e-copilot-${Date.now()}.local`,
      connector_type: "rss",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", valid: true },
    },
  });
  const conn = await create.json();

  const camp = await request.post(`${API}/campaigns`, {
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
    data: { name: `Copilot Camp ${Date.now()}`, target_industry: "Tech", positive_keywords: ["summit"] },
  });
  const campaignId = (await camp.json()).id as string;

  await request.put(`${API}/campaigns/${campaignId}/sources`, {
    data: { source_ids: [conn.id] },
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
  });

  await page.goto(`/campaigns/${campaignId}`);
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("discovery-copilot-question").fill(
    "What livestream discovery keywords should we prioritize for this campaign?",
  );
  await page.getByTestId("discovery-copilot-ask").click();
  await expect(page.getByTestId("discovery-copilot-answer")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("discovery-copilot-confidence")).toBeVisible();

  await page.getByTestId("discovery-copilot-accept").click();
  await expect(page.getByTestId("query-expansion-status")).toContainText(/pending_review|draft/i, {
    timeout: 10_000,
  });
});