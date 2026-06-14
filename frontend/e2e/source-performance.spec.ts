import { test, expect } from "@playwright/test";

test("source performance grouping and table", async ({ page }) => {
  await page.goto("/reports/source-performance");
  await expect(page.getByTestId("source-performance-report")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("source-performance-grouping-controls")).toBeVisible();

  await page.getByTestId("source-performance-preset-last_7_days").click();
  await expect(page.getByTestId("source-performance-window-label")).toBeVisible();

  await page.getByTestId("source-performance-grouping-industry").click();
  await expect(page.getByTestId("source-performance-window-label")).toContainText(/Industry|industry/i);

  await page.getByTestId("source-performance-grouping-platform").click();
  await expect(page.getByTestId("source-performance-freshness")).toBeVisible();
});