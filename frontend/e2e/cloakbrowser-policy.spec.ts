import { test, expect } from "@playwright/test";

test("admin CloakBrowser approval and blocked state visibility", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const conn = await page.request.post("/admin/connectors", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: `US025 Cloak ${Date.now()}`,
      domain: "cloak.example.com",
      connector_type: "browser",
      automation_engine: "cloakbrowser",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "browser", valid: true },
    },
  });
  expect(conn.ok()).toBeTruthy();
  const sourceId = (await conn.json()).id as string;

  await page.goto("/admin/connectors");
  await expect(page.getByTestId("admin-connectors")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("connector-row").filter({ hasText: "cloak.example.com" }).click();
  await expect(page.getByTestId("cloakbrowser-policy-panel")).toBeVisible();

  await page.getByTestId("cloakbrowser-rationale").fill("E2E governed scope");
  await page.getByTestId("cloakbrowser-request").click();
  await expect(page.getByTestId("cloakbrowser-policy-state")).toContainText(/pending/i, { timeout: 10_000 });
  await expect(page.getByTestId("cloakbrowser-blocked-reasons")).toBeVisible();

  await page.getByTestId("cloakbrowser-approve-owner").click();
  await expect(page.getByTestId("cloakbrowser-policy-state")).toContainText(/pending|approved/i);

  await page.setExtraHTTPHeaders({ "X-Actor-Role": "compliance" });
  await page.getByTestId("cloakbrowser-approve-compliance").click();
  await expect(page.getByTestId("cloakbrowser-policy-state")).toContainText(/approved/i, { timeout: 10_000 });

  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });
  await page.getByTestId("cloakbrowser-revoke").click();
  await expect(page.getByTestId("cloakbrowser-policy-state")).toContainText(/revoked/i, { timeout: 10_000 });

  const policy = await page.request.get(`/admin/cloakbrowser-policy/sources/${sourceId}`, {
    headers: { "X-Actor-Role": "admin" },
  });
  expect(policy.ok()).toBeTruthy();
  expect((await policy.json()).policy_state).toBe("revoked");
});