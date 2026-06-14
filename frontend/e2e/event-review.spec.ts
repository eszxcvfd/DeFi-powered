import { test, expect } from "@playwright/test";

test("review events after discovery with filter and source evidence", async ({ page }) => {
  const name = `Review E2E ${Date.now()}`;
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
  await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial/, { timeout: 60_000 });

  await page.getByTestId("campaign-view-events").click();
  await expect(page.getByTestId("campaign-events")).toBeVisible();
  await expect(page.getByTestId("event-list-row").first()).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("event-list-filter").fill("Webinar");
  await expect(page.getByTestId("event-list-row").first()).toBeVisible();

  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible();
  await expect(page.getByTestId("event-source-evidence")).toBeVisible();
  await expect(page.getByTestId("event-provenance-panel")).toBeVisible();
  await expect(page.getByTestId("event-confidence-summary")).toBeVisible();
});