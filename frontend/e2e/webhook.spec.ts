import { test, expect } from "@playwright/test";

test("admin webhook subscription CRUD and test send", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders({ "X-Actor-Role": "admin" });

  // Visit the new AdminWebhooks page directly.
  await page.goto("/admin/webhooks");
  await expect(page.getByTestId("admin-webhooks")).toBeVisible({
    timeout: 15_000,
  });

  // Choices endpoint must return the closed enums.
  const choices = await page.request.get(
    "/admin/webhooks/choices",
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(choices.ok()).toBeTruthy();
  const choicesBody = (await choices.json()) as {
    event_types: { value: string }[];
    delivery_statuses: { value: string }[];
  };
  expect(choicesBody.event_types.map((t) => t.value)).toContain(
    "alert.fired"
  );
  expect(choicesBody.event_types.map((t) => t.value)).toContain(
    "connector.auto_disable_triggered"
  );
  expect(choicesBody.delivery_statuses.map((s) => s.value)).toContain(
    "pending"
  );
  expect(choicesBody.delivery_statuses.map((s) => s.value)).toContain(
    "dead_letter"
  );

  // Create a subscription via the API.
  const subName = `US049 E2E ${Date.now()}`;
  const create = await page.request.post(
    "/admin/webhooks/subscriptions",
    {
      headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
      data: {
        name: subName,
        target_url: "https://siem.example.com/webhook",
        event_types: ["alert.fired", "lead.stage_changed"],
        enabled: true,
      },
    }
  );
  expect(create.ok()).toBeTruthy();
  const created = await create.json();
  expect(created.name).toBe(subName);
  expect(created.event_types).toContain("alert.fired");
  expect(created.secret_id).toBeTruthy();

  // Target URL validation rejects private IPs.
  const bad = await page.request.post(
    "/admin/webhooks/subscriptions",
    {
      headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
      data: {
        name: "Bad",
        target_url: "https://169.254.169.254/webhook",
        event_types: ["alert.fired"],
      },
    }
  );
  expect(bad.status()).toBe(400);

  // Invalid event type is rejected.
  const badEvent = await page.request.post(
    "/admin/webhooks/subscriptions",
    {
      headers: { "X-Actor-Role": "admin", "Content-Type": "application/json" },
      data: {
        name: "Bad event",
        target_url: "https://siem.example.com/webhook",
        event_types: ["not.a.real.event"],
      },
    }
  );
  expect(badEvent.status()).toBe(400);

  // List must include the new subscription.
  const list = await page.request.get(
    "/admin/webhooks/subscriptions",
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(list.ok()).toBeTruthy();
  const listBody = (await list.json()) as { items: { id: string }[] };
  expect(listBody.items.map((s) => s.id)).toContain(created.id);

  // Rotate the signing secret.
  const rotate = await page.request.post(
    `/admin/webhooks/subscriptions/${created.id}/rotate-secret`,
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(rotate.ok()).toBeTruthy();
  const rotated = await rotate.json();
  expect(rotated.last_rotated_at).toBeTruthy();

  // Test send: the target URL is unreachable
  // so the bounded path records a failed or
  // dead-letter delivery.
  const test = await page.request.post(
    `/admin/webhooks/subscriptions/${created.id}/test`,
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(test.ok()).toBeTruthy();
  const testDelivery = await test.json();
  expect(testDelivery.status).toBeTruthy();
  expect(["failed", "dead_letter"]).toContain(testDelivery.status);

  // Deliveries list must include the test delivery.
  const deliveries = await page.request.get(
    `/admin/webhooks/deliveries?subscription_id=${created.id}`,
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(deliveries.ok()).toBeTruthy();
  const deliveriesBody = (await deliveries.json()) as {
    items: { id: string }[];
  };
  expect(deliveriesBody.items.length).toBeGreaterThan(0);

  // Soft-delete the subscription for cleanup.
  const del = await page.request.delete(
    `/admin/webhooks/subscriptions/${created.id}`,
    { headers: { "X-Actor-Role": "admin" } }
  );
  expect(del.ok() || del.status() === 204).toBeTruthy();
});
