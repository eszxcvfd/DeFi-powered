import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

test.beforeEach(async () => {
  try {
    execSync("bash ../scripts/clean-e2e.sh");
  } catch (e) {
    console.error("Cleanup failed:", e);
  }
});

test("funnel report steps and cohort", async ({ page }) => {
  await page.goto("/reports/funnel");
  await expect(page.getByTestId("funnel-report")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("funnel-cohort-rule")).toBeVisible();
  await expect(page.getByTestId("funnel-steps")).toBeVisible();

  await page.getByTestId("funnel-preset-last_7_days").click();
  await expect(page.getByTestId("funnel-window-label")).toBeVisible();

  for (const key of ["event", "lead", "contact", "response", "meeting", "opportunity"]) {
    await expect(page.getByTestId(`funnel-step-${key}`)).toBeVisible();
    await expect(page.getByTestId(`funnel-step-count-${key}`)).toBeVisible();
  }
});