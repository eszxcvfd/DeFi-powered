import { test, expect } from "@playwright/test";

test("debug artifacts screenshot and list", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const conn = await page.request.post("/admin/connectors", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: `US023 Browser ${Date.now()}`,
      domain: "example.com",
      connector_type: "browser",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "browser", valid: true },
    },
  });
  expect(conn.ok()).toBeTruthy();
  const sourceId = (await conn.json()).id as string;

  const created = await page.request.post("/browser-sessions", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: { source_id: sourceId, initial_url: "https://example.com/" },
  });
  expect(created.ok()).toBeTruthy();
  const sessionId = (await created.json()).id as string;

  await page.goto(`/browser?session=${sessionId}`);
  await expect(page.getByTestId("browser-session-console")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("browser-session-state")).toContainText(/running|starting/i, { timeout: 45_000 });
  await expect(page.getByTestId("browser-debug-artifacts")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("browser-artifact-screenshot").click();
  await expect(page.getByTestId("browser-artifact-list")).toContainText(/screenshot/i, { timeout: 20_000 });

  await page.getByTestId("browser-debug-enable").click();
  await expect(page.getByTestId("browser-debug-enabled-state")).toContainText(/on/i, { timeout: 20_000 });
  await expect(page.getByTestId("browser-artifact-list")).toContainText(/console_log|trace/i, { timeout: 20_000 });
});