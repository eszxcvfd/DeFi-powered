import { test, expect } from "@playwright/test";
import {
  ensureSuccessMockConnector,
  pinCampaignToSuccessMockSource,
  runDiscoveryUntilTerminal,
} from "./helpers/discovery-fixture";

test("read-only scroll action on supervised session", async ({ page }) => {
  test.setTimeout(90_000);
  await ensureSuccessMockConnector(page);
  const name = `US021 Camp ${Date.now()}`;
  await page.goto("/campaigns/new");
  await page.getByTestId("wizard-name").fill(name);
  for (let i = 0; i < 6; i++) await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-save").click();
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });
  const campaignId = page.url().split("/campaigns/")[1]?.split(/[?#]/)[0];
  if (!campaignId) throw new Error("campaign id missing from URL");
  await pinCampaignToSuccessMockSource(page, campaignId);
  await runDiscoveryUntilTerminal(page);
  await page.getByTestId("campaign-view-events").click();
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await page.getByTestId("event-open-browser-session").click();
  await expect(page.getByTestId("browser-session-console")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("browser-session-state")).toContainText(/running|starting/i, { timeout: 25_000 });
  await expect(page.getByTestId("browser-read-only-actions")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("browser-action-scroll").click();
  await expect(page.getByTestId("browser-action-result")).toContainText(/completed/i, { timeout: 15_000 });
});