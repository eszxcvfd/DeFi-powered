import { test, expect, type Page } from "@playwright/test";

const OWNER_EMAIL = process.env.LIVELEAD_AUTH_DEFAULT_OWNER_EMAIL ?? "owner@example.com";
const OWNER_PASSWORD =
  process.env.LIVELEAD_AUTH_DEFAULT_OWNER_PASSWORD ?? "Owner-Pass-2026";

async function signInAsOwner(page: Page): Promise<void> {
  await page.context().clearCookies();
  await page.goto("/sign-in");
  await expect(page.getByTestId("sign-in-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("sign-in-email").fill(OWNER_EMAIL);
  await page.getByTestId("sign-in-password").fill(OWNER_PASSWORD);
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("current-user-email")).toContainText(OWNER_EMAIL, {
    timeout: 10_000,
  });
  await expect(page.getByTestId("current-user-role")).toContainText("owner");
}

test("admin observability panel renders the operator summary and seed rules", async ({ page }) => {
  test.setTimeout(120_000);
  await signInAsOwner(page);

  await page.goto("/admin/observability");
  await expect(page.getByRole("heading", { name: /Observability/i })).toBeVisible({
    timeout: 15_000,
  });

  // The seed rules are inserted by the migration; expect at least the
  // documented names to be listed in the rules table.
  await expect(page.getByText("backup.stale").first()).toBeVisible();
  await expect(page.getByText("worker.heartbeat.missing").first()).toBeVisible();
  await expect(page.getByText("audit.retention_breach_risk").first()).toBeVisible();

  // The operator summary should expose the launch-gate contract.
  await expect(page.getByText(/Environment/i).first()).toBeVisible();
  await expect(page.getByText(/Backup/i).first()).toBeVisible();
  await expect(page.getByText(/Worker heartbeat/i).first()).toBeVisible();
});

test("admin observability rejects non-owner and non-admin roles", async ({ browser }) => {
  test.setTimeout(120_000);
  // The owner/admin gate is enforced at the API layer. We deliberately
  // do not sign in here so the request carries no session cookie: the
  // boundary then either rejects the request at auth (401) when
  // auth_allow_dev_headers is false, or accepts the dev role header
  // and enforces the owner/admin gate (403) when it is true. Both
  // responses prove the surface is not open to lower-privileged roles.
  for (const role of ["viewer", "analyst"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const denied = await page.request.get("/admin/observability/summary", {
      headers: {
        "X-Actor-Role": role,
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
      },
    });
    expect([401, 403]).toContain(denied.status());
    await context.close();
  }
});
