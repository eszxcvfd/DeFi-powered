import { test, expect } from "@playwright/test";

test("create campaign in wizard and reopen from list", async ({ page }) => {
  const name = `E2E Campaign ${Date.now()}`;
  await page.goto("/campaigns/new");
  await expect(page.getByTestId("campaign-wizard")).toBeVisible();

  await page.getByTestId("wizard-name").fill(name);
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-industry").fill("Fintech");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByTestId("wizard-icp-industry").fill("Payments");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByTestId("wizard-sources")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByTestId("wizard-scoring-weights")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();

  const createResponse = page.waitForResponse(
    (r) => r.request().method() === "POST" && /\/campaigns$/.test(new URL(r.url()).pathname) && r.status() === 201,
  );
  await page.getByTestId("wizard-save").click();
  const created = await (await createResponse).json();
  const id = created.id as string;
  expect(id).toBeTruthy();

  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("campaign-detail-name")).toHaveText(name);
  await expect(page.getByTestId("campaign-scoring-weights")).toBeVisible();

  await page.getByRole("link", { name: "← Campaigns" }).click();
  await expect(page.getByTestId("campaign-list")).toBeVisible();

  // List UI paginates (10 rows); Playwright campaigns are nested under the E2E automation root.
  await expect
    .poll(async () => {
      const r = await page.request.get("/campaigns");
      if (!r.ok()) return false;
      const list = (await r.json()) as { id: string; name: string }[];
      return list.some((c) => c.id === id && c.name === name);
    })
    .toBeTruthy();

  const detailRes = await page.request.get(`/campaigns/${id}`);
  expect(detailRes.ok()).toBeTruthy();
  expect((await detailRes.json()).name).toBe(name);

  await page.goto(`/campaigns/${id}`);
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("campaign-detail-name")).toHaveText(name);
});