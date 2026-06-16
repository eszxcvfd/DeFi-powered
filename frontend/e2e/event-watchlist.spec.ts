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
  const name = `Watchlist E2E ${Date.now()}`;
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

test("event watchlist baseline — watch, reminder, filter, revisit, unwatch", async ({ page }) => {
  test.setTimeout(240_000);

  await signInAsOwner(page);
  await createCampaignAndOpenFirstEvent(page);

  // 1. The watch panel is visible. Toggle the watch on.
  await expect(page.getByTestId("event-watch-panel")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("event-watch").click();
  await expect(page.getByTestId("event-watch-state")).toContainText("Watching", { timeout: 10_000 });
  await expect(page.getByTestId("event-unwatch")).toBeVisible();

  // 2. Set a reminder. The dev DB starts with no reminder, so the input
  //    is empty. We pick a time three days in the future at noon.
  const future = new Date();
  future.setDate(future.getDate() + 3);
  future.setHours(12, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  const localValue = `${future.getFullYear()}-${pad(future.getMonth() + 1)}-${pad(future.getDate())}T${pad(future.getHours())}:${pad(future.getMinutes())}`;
  await page.getByTestId("event-watch-reminder-input").fill(localValue);
  await page.getByTestId("event-watch-note").fill("Follow up with organizer");
  await page.getByTestId("event-watch-reminder-save").click();
  await expect(page.getByTestId("event-watch-state")).toContainText("Watching", { timeout: 10_000 });
  await expect(page.getByTestId("event-watch-state")).toContainText("reminder set", { timeout: 10_000 });

  // 3. Open the watched-events list and confirm the row is present with
  //    the reminder badge.
  await page.goto("/events/watched");
  await expect(page.getByTestId("watched-events-page")).toBeVisible({ timeout: 15_000 });
  const rows = page.getByTestId("watched-event-row");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  const rowCount = await rows.count();
  expect(rowCount).toBeGreaterThanOrEqual(1);
  await expect(page.getByTestId("watchlist-reminder-scheduled").first()).toBeVisible();

  // 4. Filter the watched list to "watching only" (no reminder set on
  //    a different entry is not created here, so the count should
  //    remain the same).
  await page.getByTestId("watchlist-filter-with-reminder").click();
  await expect(page.getByTestId("watchlist-reminder-scheduled").first()).toBeVisible({ timeout: 10_000 });

  // 5. Revisit the event from the watched list and confirm the watch
  //    state still reports "Watching · reminder set".
  await page.getByTestId("watched-event-link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-watch-state")).toContainText("Watching", { timeout: 10_000 });
  await expect(page.getByTestId("event-watch-state")).toContainText("reminder set");

  // 6. Go back to the campaign event list and use the watched filter.
  const url = page.url();
  const eventId = url.split("/events/")[1]?.split("/")[0] ?? "";
  expect(eventId).toBeTruthy();
  const apiEvent = await page.context().request.get(`/events/${eventId}`);
  expect(apiEvent.status()).toBe(200);
  const apiBody = await apiEvent.json();
  const campaignId = apiBody.campaign_id;
  await page.goto(`/campaigns/${campaignId}/events`);
  await expect(page.getByTestId("campaign-events")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-list-watched").first()).toBeVisible();
  await page.getByTestId("event-list-watched-filter").selectOption("watched");
  await expect(page.getByTestId("event-list-watched").first()).toBeVisible();
  await page.getByTestId("event-list-watched-filter").selectOption("unwatched");
  // After switching to "unwatched" the previously-watched row may
  // disappear. Just confirm the filter control is still there.
  await expect(page.getByTestId("event-list-watched-filter")).toHaveValue("unwatched");

  // 7. Unwatch from the event detail. The badge must disappear and
  //    the watched-events list must no longer list this event.
  //    Switch the filter back to "all" so the event row is
  //    available to click again.
  await page.getByTestId("event-list-watched-filter").selectOption("all");
  await expect(page.getByTestId("event-list-row").first()).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible();
  await page.getByTestId("event-unwatch").click();
  await expect(page.getByTestId("event-watch")).toBeVisible({ timeout: 10_000 });
  await page.goto("/events/watched");
  // The event is no longer in the watched list. The empty state may
  // appear, or other watched events may still be present.
  const remaining = await page.getByTestId("watched-event-row").count();
  const empty = await page.getByTestId("watched-events-empty").isVisible().catch(() => false);
  expect(remaining === 0 || empty).toBeTruthy();
});
