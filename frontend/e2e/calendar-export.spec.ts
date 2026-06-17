import { test, expect, type Page } from "@playwright/test";

async function signInAsOwner(page: Page) {
  await page.context().clearCookies();
  await page.goto("/sign-in");
  await expect(page.getByTestId("sign-in-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("sign-in-email").fill("owner@example.com");
  await page.getByTestId("sign-in-password").fill("Owner-Pass-2026");
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("current-user-email")).toContainText("owner@example.com", { timeout: 10_000 });
}

async function createCampaignAndOpenFirstEvent(page: Page): Promise<void> {
  const name = `Calendar Export E2E ${Date.now()}`;
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
  await expect(page.getByTestId("campaign-events")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-list-row").first()).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible({ timeout: 15_000 });
}

test("event calendar export — modal, token mint, and settings panel", async ({ page }) => {
  test.setTimeout(240_000);

  await signInAsOwner(page);
  await createCampaignAndOpenFirstEvent(page);

  // 1. The calendar export section is visible on the
  //    event detail surface. Open the modal.
  await expect(page.getByTestId("event-calendar-export-section")).toBeVisible({
    timeout: 10_000,
  });
  await page.getByTestId("calendar-export-open").click();
  await expect(page.getByTestId("calendar-export-modal")).toBeVisible({
    timeout: 10_000,
  });

  // 2. The direct URL is shown. Mint a tokenized
  //    feed; the plaintext appears exactly once.
  await expect(page.getByTestId("calendar-export-direct-url")).toBeVisible();
  await page.getByTestId("calendar-export-mint-token").click();
  await expect(page.getByTestId("calendar-export-plaintext")).toBeVisible({
    timeout: 10_000,
  });
  const tokenizedUrl = await page
    .getByTestId("calendar-export-tokenized-url")
    .inputValue();
  expect(tokenizedUrl).toContain("/calendar-export/");
  expect(tokenizedUrl).toContain(".ics");

  // 3. Close the modal and visit the settings panel.
  //    The token row is visible and can be revoked.
  await page.getByTestId("calendar-export-modal-close").click();
  await page.goto("/settings/calendar-exports");
  await expect(page.getByTestId("calendar-exports-panel")).toBeVisible({
    timeout: 10_000,
  });
  const rows = page.getByTestId("calendar-exports-row");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  await expect(
    page.getByTestId("calendar-exports-row").first().getByTestId("calendar-exports-revoke"),
  ).toBeVisible();
  await page
    .getByTestId("calendar-exports-row")
    .first()
    .getByTestId("calendar-exports-revoke")
    .click();
});

test("watched events list exposes a subscribe-in-calendar action", async ({ page }) => {
  test.setTimeout(240_000);

  await signInAsOwner(page);
  await page.goto("/events/watched");
  await expect(page.getByTestId("watched-events-page")).toBeVisible({
    timeout: 10_000,
  });
  await expect(
    page.getByTestId("watched-events-subscribe-calendar"),
  ).toBeVisible();
  await page.getByTestId("watched-events-subscribe-calendar").click();
  await expect(page.getByTestId("calendar-export-modal")).toBeVisible({
    timeout: 10_000,
  });
});
