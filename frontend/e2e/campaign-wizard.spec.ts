import { test, expect } from "@playwright/test";

test("create campaign in wizard and reopen from list", async ({ page }) => {
  const name = `E2E Campaign ${Date.now()}`;
  await page.goto("/campaigns/new");
  await expect(page.getByTestId("campaign-wizard")).toBeVisible();

  await page.getByTestId("wizard-name").fill(name);
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-industry").fill("Fintech");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-icp-industry").fill("Payments");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByTestId("wizard-sources")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByTestId("wizard-scoring-weights")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-save").click();

  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("campaign-detail-name")).toHaveText(name);
  await expect(page.getByTestId("campaign-scoring-weights")).toBeVisible();

  await page.getByRole("link", { name: "← Campaigns" }).click();
  await expect(page.getByTestId("campaign-list")).toBeVisible();
  await expect(page.getByTestId("campaign-list-item").filter({ hasText: name })).toBeVisible({
    timeout: 10_000,
  });
});