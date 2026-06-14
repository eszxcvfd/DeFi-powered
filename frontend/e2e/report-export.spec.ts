import { test, expect } from "@playwright/test";

test("funnel report CSV export", async ({ page }) => {
  await page.goto("/reports/funnel");
  await expect(page.getByTestId("funnel-report")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("funnel-preset-last_7_days").click();
  await page.getByTestId("funnel-export-csv").click();
  await expect(page.getByTestId("funnel-export-success")).toBeVisible({ timeout: 15_000 });
});

test("source performance export preserves grouping context", async ({ page }) => {
  await page.goto("/reports/source-performance");
  await expect(page.getByTestId("source-performance-report")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("source-performance-grouping-industry").click();
  await page.getByTestId("source-performance-export-printable").click();
  await expect(page.getByTestId("source-performance-export-success")).toBeVisible({
    timeout: 15_000,
  });
});

test("dashboard printable export", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("dashboard-overview")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("dashboard-export-printable").click();
  await expect(page.getByTestId("dashboard-export-success")).toBeVisible({ timeout: 15_000 });
});