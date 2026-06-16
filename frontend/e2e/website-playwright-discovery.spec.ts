import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";

test("website Playwright discovery progress and reviewable events", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const e2eDomain = `e2e-website-playwright-${Date.now()}.local`;

  const create = await request.post(`${API}/admin/connectors`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: "E2E Website Playwright",
      domain: e2eDomain,
      connector_type: "browser",
      automation_engine: "playwright",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "browser", valid: true, quota_per_day: 500, quota_used_today: 0 },
    },
  });
  expect(create.ok()).toBeTruthy();
  const conn = await create.json();

  const patch = await request.patch(`${API}/admin/connectors/${conn.id}`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      rate_limit_json: {
        browser_discovery_recipe: {
          start_url: `${API}/dev/e2e-discovery-website`,
          item_selector: ".event-card",
          title_selector: ".event-title",
          link_selector: "a.event-link",
          description_selector: ".event-desc",
          wait_for_selector: ".event-list",
          max_items: 5,
          time_budget_ms: 45_000,
        },
      },
    },
  });
  expect(patch.ok()).toBeTruthy();

  const campName = `Website PW ${Date.now()}`;
  await page.goto("/campaigns/new");
  await page.getByTestId("wizard-name").fill(campName);
  for (let i = 0; i < 6; i++) {
    await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByTestId("wizard-save").click();
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  const campaignId = page.url().split("/campaigns/")[1]?.split(/[?#]/)[0];
  expect(campaignId).toBeTruthy();

  const pin = await request.put(`${API}/campaigns/${campaignId}/sources`, {
    data: { source_ids: [conn.id] },
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
      if (
        rows.some((e) => e.canonical_title.includes("US033 Website Summit")) ||
        rows.some((e) => e.canonical_title.includes("Website Summit"))
      ) {
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
});