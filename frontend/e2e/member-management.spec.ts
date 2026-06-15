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

test("member management baseline — invite, accept, role change, disable, revoke", async ({ page, request }) => {
  test.setTimeout(240_000);

  // 1. Sign in as the bootstrap owner.
  await signInAsOwner(page);

  // 2. Open the members admin surface.
  await page.goto("/admin/members");
  await expect(page.getByTestId("admin-members")).toBeVisible({ timeout: 15_000 });

  // 3. The owner appears in the current members list.
  const ownerRow = page.getByTestId("member-row").first();
  await expect(ownerRow).toBeVisible({ timeout: 10_000 });
  await expect(ownerRow).toContainText("owner@example.com");

  // 4. Invite a new analyst.
  const inviteEmail = `invitee-${Date.now()}@example.com`;
  await page.getByTestId("invite-email").fill(inviteEmail);
  await page.getByTestId("invite-role").selectOption("analyst");
  await page.getByTestId("invite-submit").click();
  const tokenCard = page.getByTestId("invite-token-card");
  await expect(tokenCard).toBeVisible({ timeout: 10_000 });
  const token = (await page.getByTestId("invite-token-value").innerText()).trim();
  expect(token.length).toBeGreaterThanOrEqual(32);

  // 5. The invite appears in the pending invitations table.
  const inviteRow = page.locator(`[data-testid="invitation-row"]`).filter({ hasText: inviteEmail });
  await expect(inviteRow).toBeVisible({ timeout: 10_000 });
  await expect(inviteRow.getByTestId("invitation-role")).toHaveText("analyst");

  // 6. The invitee accepts the invitation on a fresh context.
  const acceptContext = await page.context().browser()!.newContext();
  const acceptPage = await acceptContext.newPage();
  await acceptPage.goto(`/invitations/accept?token=${encodeURIComponent(token)}`);
  await expect(acceptPage.getByTestId("accept-invitation-page")).toBeVisible({ timeout: 15_000 });
  await acceptPage.getByTestId("accept-display-name").fill("Invited Analyst");
  await acceptPage.getByTestId("accept-password").fill("Hello-World-2026");
  await acceptPage.getByTestId("accept-submit").click();
  await expect(acceptPage.getByTestId("accept-success")).toBeVisible({ timeout: 10_000 });
  // The session is established and the page redirects to the dashboard.
  await expect(acceptPage).toHaveURL(/\/$|\/admin\/members|\/campaigns|\/events/, { timeout: 10_000 });
  await acceptContext.close();

  // 7. Refresh the members list — the new analyst now appears as a member.
  await page.reload();
  await expect(page.getByTestId("admin-members")).toBeVisible({ timeout: 10_000 });
  const newRow = page.locator(`[data-testid="member-row"]`).filter({ hasText: inviteEmail });
  await expect(newRow).toBeVisible({ timeout: 10_000 });
  await expect(newRow.getByTestId("member-state")).toContainText("active");

  // 8. Disable the new member.
  await newRow.getByTestId("member-disable").click();
  await expect(newRow.getByTestId("member-state")).toContainText("disabled", { timeout: 10_000 });

  // 9. Re-enable, then change role to reviewer.
  await newRow.getByTestId("member-enable").click();
  await expect(newRow.getByTestId("member-state")).toContainText("active", { timeout: 10_000 });
  await newRow.getByTestId("member-role-select").selectOption("reviewer");
  // The page should reflect the new role after the change.
  await expect(newRow.getByTestId("member-role-select")).toHaveValue("reviewer", { timeout: 10_000 });

  // 10. Revoke the new member's access.
  page.once("dialog", (dialog) => {
    void dialog.accept();
  });
  await newRow.getByTestId("member-revoke").click();
  await expect(newRow.getByTestId("member-state")).toContainText("revoked", { timeout: 10_000 });

  // 11. The audit log must include invite / accept / role change / disable / revoke entries.
  await page.goto("/admin/audit-log");
  await expect(page.getByTestId("admin-audit-log")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("filter-action-family").selectOption("member");
  const rows = page.getByTestId("audit-row");
  await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  const actions: string[] = [];
  for (let i = 0; i < (await rows.count()); i++) {
    const text = await rows.nth(i).innerText();
    actions.push(text);
  }
  const combined = actions.join("\n");
  expect(combined).toMatch(/member\.invited/);
  expect(combined).toMatch(/member\.invitation\.accepted/);
  expect(combined).toMatch(/member\.role\.changed/);
  expect(combined).toMatch(/member\.disabled/);
  expect(combined).toMatch(/member\.enabled/);
  expect(combined).toMatch(/member\.access\.revoked/);
});
