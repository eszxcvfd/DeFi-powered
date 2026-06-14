import { test, expect } from "@playwright/test";

test("admin browser profile lifecycle and governed session", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  await page.goto("/admin/browser-profiles");
  await expect(page.getByTestId("admin-browser-profiles")).toBeVisible({ timeout: 15_000 });

  const profileName = `US024 ${Date.now()}`;
  await page.getByTestId("browser-profile-name").fill(profileName);
  await page.getByTestId("browser-profile-create-btn").click();
  await expect(page.getByTestId("browser-profile-row").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("browser-profile-state").first()).toContainText(/active/i);

  const conn = await page.request.post("/admin/connectors", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: `US024 Browser ${Date.now()}`,
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

  const profiles = await page.request.get("/admin/browser-profiles", {
    headers: { "X-Actor-Role": "admin" },
  });
  const profileId = (await profiles.json()).find((p: { name: string }) => p.name === profileName)?.id;
  expect(profileId).toBeTruthy();

  const session = await page.request.post("/browser-sessions", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      source_id: sourceId,
      initial_url: "https://example.com/",
      browser_profile_id: profileId,
    },
  });
  expect(session.ok()).toBeTruthy();

  await page.getByTestId("browser-profile-lock").first().click();
  await expect(page.getByTestId("browser-profile-blocked").first()).toBeVisible({ timeout: 10_000 });

  const blocked = await page.request.post("/browser-sessions", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      source_id: sourceId,
      initial_url: "https://example.com/",
      browser_profile_id: profileId,
    },
  });
  expect(blocked.status()).toBe(409);
});