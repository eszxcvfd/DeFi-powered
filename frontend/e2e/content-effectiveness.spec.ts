import { test, expect } from "@playwright/test";

test("content effectiveness grouping and correlation note", async ({ page }) => {
  await page.goto("/reports/content-effectiveness");
  await expect(page.getByTestId("content-effectiveness-report")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("content-effectiveness-correlation-note")).toBeVisible();
  await page.getByTestId("content-effectiveness-grouping-tone").click();
  await expect(page.getByTestId("content-effectiveness-window-label")).toBeVisible();
  await page.getByTestId("content-effectiveness-preset-last_7_days").click();
  await expect(page.getByTestId("content-effectiveness-freshness")).toBeVisible();
});