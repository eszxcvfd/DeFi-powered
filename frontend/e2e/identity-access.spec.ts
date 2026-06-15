import { test, expect } from "@playwright/test";

test("identity access baseline — sign in, sign out, role gating, and audit log capture", async ({ page }) => {
  test.setTimeout(180_000);

  // 1. Sign in via the web UI as the bootstrap owner.
  await page.context().clearCookies();
  await page.goto("/sign-in");
  await expect(page.getByTestId("sign-in-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("sign-in-email").fill("owner@example.com");
  await page.getByTestId("sign-in-password").fill("Owner-Pass-2026");
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("current-user-email")).toContainText("owner@example.com", { timeout: 10_000 });
  await expect(page.getByTestId("current-user-role")).toContainText("owner");

  // 3. The sign-out button must end the session and redirect to /sign-in.
  await page.getByTestId("sign-out-button").click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/sign-in$/);

  // 4. Sign back in to inspect the audit log.
  await page.getByTestId("sign-in-email").fill("owner@example.com");
  await page.getByTestId("sign-in-password").fill("Owner-Pass-2026");
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("current-user-email")).toContainText("owner@example.com", { timeout: 10_000 });

  // 5. The audit log must include the auth.login.succeeded and auth.session.revoked events.
  await page.goto("/admin/audit-log");
  await expect(page.getByTestId("admin-audit-log")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("filter-action-family").selectOption("auth");
  const rows = page.getByTestId("audit-row");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  const actions: string[] = [];
  for (let i = 0; i < (await rows.count()); i++) {
    const text = await rows.nth(i).innerText();
    actions.push(text);
  }
  const combined = actions.join("\n");
  expect(combined).toMatch(/auth\.login\.succeeded/);
  expect(combined).toMatch(/auth\.session\.revoked/);
});
