import { test, expect } from "@playwright/test";

test("event detail creates engagement plan and updates task", async ({ page }) => {
  const name = `Engagement E2E ${Date.now()}`;
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
  await page.getByTestId("event-rescore").click();
  await expect(page.getByTestId("event-total-score")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("engagement-create").click();
  await expect(page.getByTestId("engagement-task").first()).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("engagement-task-status").first().selectOption("IN_PROGRESS");
  await expect(page.getByTestId("engagement-task-status").first()).toHaveValue("IN_PROGRESS");
});