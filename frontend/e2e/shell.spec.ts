import { test, expect } from "@playwright/test";

test("campaign list shell renders", async ({ page }) => {
  await page.goto("/campaigns");
  await expect(page.getByTestId("campaign-list")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Campaigns" })).toBeVisible();
});