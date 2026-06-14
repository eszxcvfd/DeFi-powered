import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

test.beforeEach(async () => {
  try {
    execSync("bash ../scripts/clean-e2e.sh");
  } catch (e) {
    console.error("Cleanup failed:", e);
  }
});

test("dashboard overview time range and widget states", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("dashboard-overview")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("dashboard-range-controls")).toBeVisible();

  await page.getByTestId("dashboard-preset-last_7_days").click();
  await expect(page.getByTestId("dashboard-window-label")).toContainText(/last_7_days|Window:/);

  const discovered = page.getByTestId("dashboard-widget-events_discovered");
  await expect(discovered).toBeVisible();
  const unavail = page.getByTestId("widget-events_discovered-unavailable");
  const empty = page.getByTestId("widget-events_discovered-empty");
  const value = page.getByTestId("widget-events_discovered-value");
  await expect(unavail.or(empty).or(value)).toBeVisible();

  await expect(page.getByTestId("widget-events_discovered-freshness")).toBeVisible();
  await expect(page.getByTestId("dashboard-widget-opportunities")).toBeVisible();
  await expect(page.getByTestId("widget-opportunities-unavailable")).toBeVisible();
});