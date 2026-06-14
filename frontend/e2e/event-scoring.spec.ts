import { test, expect } from "@playwright/test";

test("campaign events list shows score after rescore", async ({ page }) => {
  const name = `Score E2E ${Date.now()}`;
  await page.goto("/campaigns/new");
  await page.getByTestId("wizard-name").fill(name);
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-industry").fill("Fintech");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-icp-industry").fill("Payments");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-save").click();
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial|failed/, {
    timeout: 60_000,
  });

  await page.getByTestId("campaign-view-events").click();
  await expect(page.getByTestId("campaign-events")).toBeVisible({ timeout: 10_000 });

  const row = page.getByTestId("event-list-row").first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible();

  const panel = page.getByTestId("event-score-panel");
  if (await panel.getByText(/not calculated/i).isVisible().catch(() => false)) {
    await page.getByTestId("event-rescore").click();
  }
  await expect(page.getByTestId("event-total-score")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("event-rescore").click();
  await expect(page.getByTestId("event-total-score")).toBeVisible();
});