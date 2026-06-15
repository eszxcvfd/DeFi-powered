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

test("notification baseline — inbox, preferences, run scan, read & dismiss", async ({ page }) => {
  test.setTimeout(180_000);

  await signInAsOwner(page);

  // 1. Open the inbox page.
  await page.goto("/notifications");
  await expect(page.getByTestId("notification-inbox-page")).toBeVisible({ timeout: 15_000 });
  const initialUnread = await page.getByTestId("inbox-unread-count").innerText();

  // 2. Open the preferences page and confirm the seeded matrix is shown.
  await page.goto("/notification-preferences");
  await expect(page.getByTestId("notification-preferences-page")).toBeVisible({ timeout: 15_000 });
  const rows = page.getByTestId("preference-row");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  const rowCount = await rows.count();
  expect(rowCount).toBeGreaterThanOrEqual(6);

  // 3. Toggle the email checkbox for `event_upcoming` off and save.
  const eventUpcomingEmail = page.getByTestId("pref-email-event_upcoming");
  const beforeChecked = await eventUpcomingEmail.isChecked();
  if (beforeChecked) {
    await eventUpcomingEmail.uncheck();
  } else {
    await eventUpcomingEmail.check();
  }
  await page.getByTestId("preferences-save").click();
  await expect(page.getByTestId("preferences-saved")).toBeVisible({ timeout: 10_000 });

  // 4. Run the admin scan and confirm at least one in-app row is created
  //    for the current owner.
  await page.goto("/notifications");
  await expect(page.getByTestId("notification-inbox-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("run-scan").click();
  await expect(page.getByTestId("scan-result")).toBeVisible({ timeout: 15_000 });
  const resultText = await page.getByTestId("scan-result").innerText();
  expect(resultText).toMatch(/Scan complete/);

  // 5. The inbox now contains at least one row.
  const inboxRows = page.getByTestId("notification-row");
  await expect(inboxRows.first()).toBeVisible({ timeout: 10_000 });
  const inboxCount = await inboxRows.count();
  expect(inboxCount).toBeGreaterThanOrEqual(1);

  // 6. The unread counter increased or stayed the same (the scan may
  //    have produced zero or more candidates, depending on fixture
  //    data; the counter must not decrease below the original count).
  const afterUnread = await page.getByTestId("inbox-unread-count").innerText();
  const initialNum = parseInt(initialUnread.split(" ")[0] || "0", 10);
  const afterNum = parseInt(afterUnread.split(" ")[0] || "0", 10);
  expect(afterNum).toBeGreaterThanOrEqual(initialNum);

  // 7. Mark the first notification as read.
  const first = inboxRows.first();
  await first.getByTestId("notification-mark-read").click();
  await expect(first.getByTestId("notification-title")).toBeVisible();

  // 8. Dismiss the same notification.
  await first.getByTestId("notification-dismiss").click();
  // The dismissed state is rendered without a "Dismiss" button.
  await expect(first.getByTestId("notification-mark-read")).toHaveCount(0, { timeout: 10_000 });

  // 9. The audit log must mention preference changes and delivery events.
  await page.goto("/admin/audit-log");
  await expect(page.getByTestId("admin-audit-log")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("filter-action-family").selectOption("notification");
  const rows2 = page.getByTestId("audit-row");
  await expect(rows2.first()).toBeVisible({ timeout: 10_000 });
  const actions: string[] = [];
  for (let i = 0; i < (await rows2.count()); i++) {
    actions.push(await rows2.nth(i).innerText());
  }
  const combined = actions.join("\n");
  expect(combined).toMatch(/notification\.preference_changed/);
  expect(combined).toMatch(/notification\.delivered/);
});
