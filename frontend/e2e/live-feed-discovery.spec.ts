import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";
const E2E_DOMAIN = "e2e-live-feed.local";

test("live feed discovery progress and reviewable events", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  await page.goto("/admin/connectors");
  await page.getByTestId("connector-name").fill("E2E Live RSS");
  await page.getByTestId("connector-domain").fill(E2E_DOMAIN);
  await page.getByTestId("connector-add").click();

  const connectors = await request.get(`${API}/admin/connectors`, {
    headers: { "X-Actor-Role": "admin" },
  });
  const conn = (await connectors.json()).find((c: { domain: string }) => c.domain === E2E_DOMAIN);
  expect(conn).toBeTruthy();

  const patch = await request.patch(`${API}/admin/connectors/${conn.id}`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      approved: true,
      enabled: true,
      policy: { access_mode: "feed", valid: true, quota_per_day: 500, quota_used_today: 0 },
      rate_limit_json: { feed_url: `${API}/dev/e2e-discovery-rss` },
    },
  });
  expect(patch.ok()).toBeTruthy();

  const fixtureProbe = await request.get(`${API}/dev/e2e-discovery-rss`);
  expect(fixtureProbe.ok()).toBeTruthy();
  expect(await fixtureProbe.text()).toContain("E2E Live Feed Summit");

  const campName = `Live Feed ${Date.now()}`;
  await page.goto("/campaigns/new");
  await page.getByTestId("wizard-name").fill(campName);
  for (let i = 0; i < 6; i++) {
    await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByTestId("wizard-save").click();
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  const campaignId = page.url().split("/campaigns/")[1]?.split(/[?#]/)[0];
  expect(campaignId).toBeTruthy();

  const runnable = await request.get(`${API}/campaigns/runnable-sources`);
  const source = (await runnable.json()).find((s: { domain: string }) => s.domain === E2E_DOMAIN);
  expect(source).toBeTruthy();

  const pin = await request.put(`${API}/campaigns/${campaignId}/sources`, {
    data: { source_ids: [source.id] },
    headers: { "Content-Type": "application/json", "X-Actor-Role": "admin" },
  });
  expect(pin.ok()).toBeTruthy();

  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-progress")).toBeVisible({ timeout: 20_000 });

  let foundTitle = false;
  for (let i = 0; i < 180; i++) {
    const ev = await request.get(`${API}/campaigns/${campaignId}/events`, {
      headers: { "X-Actor-Role": "admin" },
    });
    if (ev.ok()) {
      const rows = (await ev.json()) as { canonical_title: string }[];
      if (rows.some((e) => e.canonical_title.includes("E2E Live Feed Summit"))) {
        foundTitle = true;
        break;
      }
    }
    await page.waitForTimeout(500);
  }
  expect(foundTitle).toBeTruthy();

  await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial/, {
    timeout: 15_000,
  });

  await page.goto(`/campaigns/${campaignId}/events`);
  await expect(page.getByText("E2E Live Feed Summit")).toBeVisible({ timeout: 15_000 });
});