import { test, expect } from "@playwright/test";
import {
  ensureSuccessMockConnector,
  pinCampaignToSuccessMockSource,
  runDiscoveryUntilTerminal,
} from "./helpers/discovery-fixture";

test("supervised browser session from event", async ({ page }) => {
  test.setTimeout(90_000);
  await ensureSuccessMockConnector(page);
  const name = `Browser E2E ${Date.now()}`;
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
  const campaignId = page.url().split("/campaigns/")[1]?.split(/[?#]/)[0];
  if (!campaignId) throw new Error("campaign id missing from URL");
  await pinCampaignToSuccessMockSource(page, campaignId);
  await runDiscoveryUntilTerminal(page);
  await page.getByTestId("campaign-view-events").click();
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-browser-launch-panel")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-browser-source-select")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("event-open-browser-session").click();
  await expect(page.getByTestId("browser-session-console")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("browser-session-state")).toContainText(/running|starting|queued/i, {
    timeout: 20_000,
  });
  await expect(page.getByTestId("browser-session-runtime")).toContainText(/playwright/i);

  await page.getByTestId("browser-session-stop").click();
  await expect(page.getByTestId("browser-session-stopped")).toBeVisible({ timeout: 15_000 });
});