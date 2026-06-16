import { test, expect, type Page, type APIRequestContext } from "@playwright/test";

async function signInAsOwner(page: Page) {
  await page.context().clearCookies();
  await page.goto("/sign-in");
  await expect(page.getByTestId("sign-in-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("sign-in-email").fill("owner@example.com");
  await page.getByTestId("sign-in-password").fill("Owner-Pass-2026");
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("current-user-email")).toContainText("owner@example.com", { timeout: 10_000 });
}

async function seedInAppNotification(request: APIRequestContext): Promise<string> {
  // POST to the in-app notification list endpoint is not allowed for
  // arbitrary user data, so the e2e uses the admin scan to create at
  // least one in-app row for the bootstrap owner. The integration
  // test covers the deeper scan path; the e2e just needs the inbox
  // populated.
  const r = await request.post("/admin/notifications/scan", {
    data: { include_reminders: true, include_events: true, lead_minutes: 60 },
  });
  expect(r.status(), `scan returned ${r.status()}: ${await r.text()}`).toBe(200);
  // Read back the inbox to ensure at least one row exists. If the
  // scan produced zero candidates, the test continues with the
  // empty-state UI checks instead of the row-level checks.
  const inbox = await request.get("/notifications");
  expect(inbox.status()).toBe(200);
  const body = await inbox.json();
  return body.items?.[0]?.id ?? "";
}

test("notification baseline — inbox, preferences, run scan, read & dismiss", async ({ page }) => {
  test.setTimeout(180_000);

  await signInAsOwner(page);
  // The page's context shares cookies with the page.request, so use
  // the page-scoped request to keep the auth cookie available.
  const api = page.context().request;

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

  // 4. Trigger the admin scan from the API and confirm a row appears in
  //    the inbox when at least one candidate is generated. The
  //    bootstrap dev DB does not always have an event within the lead
  //    window, so the assertion is conditional on having at least one
  //    row in the inbox afterwards.
  const seedId = await seedInAppNotification(api);

  await page.goto("/notifications");
  await expect(page.getByTestId("notification-inbox-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("run-scan").click();
  await expect(page.getByTestId("scan-result")).toBeVisible({ timeout: 15_000 });
  const resultText = await page.getByTestId("scan-result").innerText();
  expect(resultText).toMatch(/Scan complete/);

  // 5. The inbox now contains at least one row when the scan
  //    produced a candidate. The dev DB may have zero in-app rows
  //    if no event is within the lead window, so the row assertions
  //    are conditional on the seed call having produced an id.
  if (seedId) {
    const inboxRows = page.getByTestId("notification-row");
    await expect(inboxRows.first()).toBeVisible({ timeout: 10_000 });
    const inboxCount = await inboxRows.count();
    expect(inboxCount).toBeGreaterThanOrEqual(1);

    // 6. Mark the first notification as read and then dismiss it.
    const first = inboxRows.first();
    await first.getByTestId("notification-mark-read").click();
    await expect(first.getByTestId("notification-title")).toBeVisible();
    await first.getByTestId("notification-dismiss").click();
    await expect(first.getByTestId("notification-mark-read")).toHaveCount(0, { timeout: 10_000 });
  } else {
    // Even with no candidates, the empty-state UI must render.
    await expect(page.getByTestId("inbox-empty")).toBeVisible({ timeout: 10_000 });
  }

  // 7. The unread counter never decreases below the original count.
  const afterUnread = await page.getByTestId("inbox-unread-count").innerText();
  const initialNum = parseInt(initialUnread.split(" ")[0] || "0", 10);
  const afterNum = parseInt(afterUnread.split(" ")[0] || "0", 10);
  expect(afterNum).toBeGreaterThanOrEqual(initialNum);

  // 8. The audit log must mention preference changes. Delivery and
  //    suppression actions appear when the scan produced candidates.
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
  // The scan may produce zero in-app rows; in that case the
  // notification.delivered audit may or may not appear. The
  // integration test covers the full path.
});
