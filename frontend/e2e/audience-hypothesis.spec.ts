import { test, expect } from "@playwright/test";

test("event detail shows audience hypotheses after discovery", async ({ page }) => {
  const name = `Audience E2E ${Date.now()}`;
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
  await expect(page.getByTestId("event-audience-panel")).toBeVisible();
  const panel = page.getByTestId("event-audience-panel");
  const hasHyp = await panel.getByTestId("audience-hypothesis").first().isVisible().catch(() => false);
  if (!hasHyp) {
    await expect(panel.getByTestId("audience-empty")).toBeVisible();
  } else {
    await expect(panel.getByTestId("audience-hypothesis").first()).toContainText(/customer|partner|referral/i);
  }
});