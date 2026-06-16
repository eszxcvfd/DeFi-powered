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
  const name = `Overrides E2E ${Date.now()}`;
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

test("event manual override baseline — edit, see history, clear override", async ({ page }) => {
  test.setTimeout(240_000);

  await signInAsOwner(page);
  await createCampaignAndOpenFirstEvent(page);

  // 1. The override panel and history panel are visible on detail.
  await expect(page.getByTestId("event-overrides-panel")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("event-history-panel")).toBeVisible();

  // 2. The empty state is shown because no overrides exist yet.
  await expect(page.getByTestId("event-override-empty")).toBeVisible();

  // 3. Save an override on the `organizer` field. The first
  //    editable row corresponds to `canonical_title`, but the
  //    organizer row is also editable. Find the organizer input
  //    by walking the editable rows.
  const organizerRow = page
    .getByTestId("event-override-editable-row")
    .filter({ hasText: "organizer" });
  await expect(organizerRow).toBeVisible();
  await organizerRow.getByTestId("event-override-input").fill("Acme GmbH");
  await organizerRow.getByTestId("event-override-save").click();

  // 4. The override appears in the active list with the new value
  //    and the source-backed baseline.
  const overrideRow = page
    .getByTestId("event-override-row")
    .filter({ hasText: "organizer" });
  await expect(overrideRow).toBeVisible({ timeout: 10_000 });
  await expect(overrideRow.getByTestId("event-override-effective")).toContainText("Acme GmbH");

  // 5. The history panel shows the upserted action.
  const historyRows = page.getByTestId("event-history-row");
  await expect(historyRows.first()).toBeVisible({ timeout: 10_000 });
  const firstHistoryText = await historyRows.first().innerText();
  expect(firstHistoryText).toMatch(/Override set on organizer/);

  // 6. Clear the override. The active list shrinks and the source
  //    value is restored.
  await overrideRow.getByTestId("event-override-clear").click();
  await expect(page.getByTestId("event-override-empty")).toBeVisible({ timeout: 10_000 });
  // The history panel re-fetches on the same refresh key, so we
  // wait for at least two rows (the original upsert and the clear).
  await expect(async () => {
    const count = await page.getByTestId("event-history-row").count();
    if (count < 2) throw new Error(`expected >= 2 history rows, saw ${count}`);
  }).toPass({ timeout: 10_000 });

  // 7. The history panel now contains both the upsert and the
  //    clear action in descending order.
  const allHistoryText = await page
    .getByTestId("event-history-list")
    .innerText();
  expect(allHistoryText).toMatch(/Override cleared on organizer/);
  expect(allHistoryText).toMatch(/Override set on organizer/);
});
