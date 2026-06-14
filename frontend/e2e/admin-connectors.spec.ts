import { test, expect } from "@playwright/test";

test("admin sees connector registry without plaintext secrets", async ({ page }) => {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });
  await page.goto("/admin/connectors");
  await expect(page.getByTestId("admin-connectors")).toBeVisible();
  const unique = `Playwright RSS ${Date.now()}`;
  await page.getByTestId("connector-name").fill(unique);
  await page.getByTestId("connector-domain").fill(`pw-${Date.now()}.example.com`);
  await page.getByTestId("connector-add").click();
  await expect(page.getByTestId("connector-row").filter({ hasText: unique })).toBeVisible({
    timeout: 10_000,
  });
  const secretCell = page.getByTestId("connector-secret").first();
  await expect(secretCell).not.toContainText("api-key");
  await expect(secretCell).not.toContainText("sk-");
});