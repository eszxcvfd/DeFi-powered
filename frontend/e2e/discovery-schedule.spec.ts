import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";

test("create discovery schedule, preview next run, pause and resume", async ({ page, request }) => {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const create = await request.post(`${API}/admin/connectors`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: "E2E Schedule Source",
      domain: `e2e-schedule-${Date.now()}.local`,
      connector_type: "rss",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", valid: true, quota_per_day: 500, quota_used_today: 0 },
    },
  });
  expect(create.ok()).toBeTruthy();
  const conn = await create.json();

  const campName = `Schedule Camp ${Date.now()}`;
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

  const sched = await request.post(`${API}/campaigns/${campaignId}/discovery-schedules`, {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: { recurrence: { kind: "daily", timezone: "UTC", hour: 9, minute: 0 } },
  });
  expect(sched.ok()).toBeTruthy();

  await page.reload();
  await expect(page.getByTestId("discovery-schedule-row")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("discovery-schedule-next-run")).toContainText(/Next run:/i);

  await page.getByTestId("discovery-schedule-pause").click();
  await expect(page.getByTestId("discovery-schedule-state")).toContainText(/paused/i);

  await page.getByTestId("discovery-schedule-resume").click();
  await expect(page.getByTestId("discovery-schedule-state")).toContainText(/enabled/i);
});