import { test, expect } from "@playwright/test";

test("run mock discovery from campaign detail", async ({ page }) => {
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });
  await page.goto("/admin/connectors");
  await page.getByTestId("connector-name").fill("E2E Mock");
  await page.getByTestId("connector-domain").fill("success-mock.example.com");
  await page.getByTestId("connector-add").click();

  const name = `Discovery Camp ${Date.now()}`;
  await page.goto("/campaigns/new");
  await page.getByTestId("wizard-name").fill(name);
  for (let i = 0; i < 6; i++) {
    await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByTestId("wizard-save").click();
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-progress")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("discovery-status")).toHaveText(/succeeded|partial|failed|cancelled|needs_user_action/, {
    timeout: 25_000,
  });
});