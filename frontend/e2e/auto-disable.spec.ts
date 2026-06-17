import { test, expect } from "@playwright/test";

test("admin connector auto-disable panel renders choices and rules", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  // Seed a connector.
  const conn = await page.request.post("/admin/connectors", {
    headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
    data: {
      name: `US048 Auto ${Date.now()}`,
      domain: "auto.example.com",
      connector_type: "rss",
      automation_engine: "none",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", valid: true },
    },
  });
  expect(conn.ok()).toBeTruthy();
  const sourceId = (await conn.json()).id as string;

  await page.goto("/admin/connectors");
  await expect(page.getByTestId("admin-connectors")).toBeVisible({ timeout: 15_000 });

  // Choices endpoint must return the closed enums.
  const choices = await page.request.get(
    "/admin/connectors/auto-disable/choices",
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(choices.ok()).toBeTruthy();
  const body = (await choices.json()) as {
    triggers: { value: string }[];
    event_statuses: { value: string }[];
  };
  expect(body.triggers.map((t) => t.value)).toContain("health_unhealthy");
  expect(body.triggers.map((t) => t.value)).toContain("error_spike");
  expect(body.event_statuses.map((s) => s.value)).toContain("active");

  // Create a rule via the API.
  const create = await page.request.post(
    "/admin/connectors/auto-disable/rules",
    {
      headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
      data: {
        source_id: sourceId,
        trigger: "health_unhealthy",
        threshold_value: 0.0,
        consecutive_breaches: 3,
        cooldown_seconds: 900,
      },
    }
  );
  expect(create.ok()).toBeTruthy();
  const ruleId = (await create.json()).id as string;

  // List must show the new rule.
  const list = await page.request.get(
    "/admin/connectors/auto-disable/rules",
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(list.ok()).toBeTruthy();
  const listBody = (await list.json()) as { items: { id: string }[] };
  expect(listBody.items.map((r) => r.id)).toContain(ruleId);

  // Delete the rule for cleanup.
  const del = await page.request.delete(
    `/admin/connectors/auto-disable/rules/${ruleId}`,
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(del.ok() || del.status() === 204).toBeTruthy();
});
