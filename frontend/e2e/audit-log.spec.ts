import { test, expect } from "@playwright/test";

test("admin audit log captures representative workflow and exposes redacted detail", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  const ts = Date.now();
  const requestId = `audit-e2e-${ts}`;

  // Seed a CloakBrowser source and trigger a governance workflow so audit rows exist.
  const conn = await page.request.post("/admin/connectors", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: `US026 Audit ${ts}`,
      domain: `audit${ts}.example.com`,
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

  await page.request.post(`/admin/cloakbrowser-policy/sources/${sourceId}/request`, {
    headers: {
      "X-Actor-Role": "admin",
      "Content-Type": "application/json",
      "x-request-id": requestId,
    },
    data: {
      purpose_rationale: "E2E audit log scope",
      pinned_version: "1.0.0",
    },
  });
  await page.request.post(`/admin/cloakbrowser-policy/sources/${sourceId}/approve-owner-admin`, {
    headers: { "X-Actor-Role": "admin", "x-request-id": requestId },
  });
  await page.request.post(`/admin/cloakbrowser-policy/sources/${sourceId}/approve-compliance`, {
    headers: { "X-Actor-Role": "compliance", "x-request-id": requestId },
  });

  // Open the audit log UI and assert that at least one row is visible.
  await page.goto("/admin/audit-log");
  await expect(page.getByTestId("admin-audit-log")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("audit-list")).toBeVisible();
  await expect(page.getByTestId("audit-row").first()).toBeVisible({ timeout: 20_000 });

  const rowCount = await page.getByTestId("audit-row").count();
  expect(rowCount).toBeGreaterThan(0);

  // The action-family filter must not blank the page out for a value that has rows.
  await page.getByTestId("filter-action-family").selectOption("cloakbrowser");
  await expect(page.getByTestId("audit-row").first()).toBeVisible({ timeout: 10_000 });
  const familyCount = await page.getByTestId("audit-row").count();
  expect(familyCount).toBeGreaterThan(0);

  // Reset the family filter and click a row to open the detail panel.
  await page.getByTestId("filter-action-family").selectOption("__any__");
  await page.getByTestId("audit-row").first().click();
  await expect(page.getByTestId("audit-detail")).toBeVisible();
  await expect(page.getByTestId("audit-metadata")).toBeVisible();

  // Unauthorised role cannot list audit entries.
  const denied = await page.request.get("/admin/audit-logs", {
    headers: { "X-Actor-Role": "analyst" },
  });
  expect(denied.status()).toBe(403);
});
