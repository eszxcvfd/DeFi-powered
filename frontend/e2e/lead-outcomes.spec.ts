import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

test.beforeEach(async () => {
  try {
    execSync("bash ../scripts/clean-e2e.sh");
  } catch (e) {
    console.error("Cleanup failed:", e);
  }
});

test("record lead contact outcome in timeline", async ({ page }) => {
  const name = `Outcome E2E ${Date.now()}`;
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
  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial/, { timeout: 60_000 });
  await page.getByTestId("campaign-view-events").click();
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await page.getByTestId("event-create-lead").click();
  await expect(page.getByTestId("event-leads-panel")).toContainText(/linked lead/i, { timeout: 15_000 });
  await page.getByRole("link", { name: "Leads" }).click();
  await page.getByTestId("lead-row").first().click();
  await expect(page.getByTestId("lead-record-outcome")).toBeVisible();
  await page.getByTestId("lead-outcome-type").selectOption("contact");
  await page.getByTestId("lead-outcome-notes").fill("Initial outreach call");
  await page.getByTestId("lead-record-outcome-submit").click();
  await expect(page.getByTestId("lead-latest-outcome")).toContainText(/contact/i, { timeout: 15_000 });
  await expect(page.getByTestId("lead-activity-list")).toContainText(/outcome_recorded|contact/i);
});