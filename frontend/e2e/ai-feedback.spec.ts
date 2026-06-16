import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";
const E2E_DOMAIN = "e2e-live-feed.local";
const ADMIN = { "X-Actor-Role": "admin" };

test("copilot and audience feedback persist on refresh", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders(ADMIN);

  await page.goto("/admin/connectors");
  await page.getByTestId("connector-name").fill("E2E AI Feedback RSS");
  await page.getByTestId("connector-domain").fill(E2E_DOMAIN);
  await page.getByTestId("connector-add").click();

  const connectors = await request.get(`${API}/admin/connectors`, { headers: ADMIN });
  const conn = (await connectors.json()).find((c: { domain: string }) => c.domain === E2E_DOMAIN);
  expect(conn).toBeTruthy();

  await request.patch(`${API}/admin/connectors/${conn.id}`, {
    headers: { ...ADMIN, "Content-Type": "application/json" },
    data: {
      approved: true,
      enabled: true,
      policy: { access_mode: "feed", valid: true, quota_per_day: 500, quota_used_today: 0 },
      rate_limit_json: { feed_url: `${API}/dev/e2e-discovery-rss` },
    },
  });

  const camp = await request.post(`${API}/campaigns`, {
    headers: { ...ADMIN, "Content-Type": "application/json" },
    data: {
      name: `AI Feedback Camp ${Date.now()}`,
      target_industry: "Fintech",
      product_or_service_focus: "Payments",
      positive_keywords: ["webinar", "payments", "fintech"],
      icp: {
        industry: "Payments",
        organization_type: "SaaS",
        company_size: "",
        role_or_title_targets: [],
        country_or_region: "EU",
        pain_points: [],
        use_cases: [],
        positive_keywords: [],
        excluded_keywords: [],
      },
    },
  });
  expect(camp.ok()).toBeTruthy();
  const campaignId = (await camp.json()).id as string;

  await request.put(`${API}/campaigns/${campaignId}/sources`, {
    data: { source_ids: [conn.id] },
    headers: { ...ADMIN, "Content-Type": "application/json" },
  });

  await page.goto(`/campaigns/${campaignId}`);
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("discovery-copilot-question").fill(
    "What livestream discovery keywords should we prioritize for this campaign?",
  );
  await page.getByTestId("discovery-copilot-ask").click();
  await expect(page.getByTestId("discovery-copilot-answer")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("copilot-feedback-helpful").click();
  await expect(page.getByTestId("ai-feedback-current")).toContainText("helpful");

  await page.getByTestId("run-discovery").click();
  await expect(page.getByTestId("discovery-status")).toContainText(/succeeded|partial/, { timeout: 90_000 });

  const eventsRes = await request.get(`${API}/campaigns/${campaignId}/events`, { headers: ADMIN });
  expect(eventsRes.ok()).toBeTruthy();
  const events = (await eventsRes.json()) as { id: string }[];
  expect(events.length).toBeGreaterThan(0);

  const eventId = events[0].id;
  await request.post(`${API}/events/${eventId}/rescore`, { headers: ADMIN });
  await request.post(`${API}/events/${eventId}/audience/refresh`, { headers: ADMIN });
  const detail = await request.get(`${API}/events/${eventId}`, { headers: ADMIN });
  const hyps = (await detail.json()).audience?.hypotheses ?? [];
  expect(hyps.length, "live RSS event should yield audience hypotheses").toBeGreaterThan(0);

  await page.getByTestId("campaign-view-events").click();
  await expect(page.getByTestId("event-list-row").first()).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("event-list-row").first().getByRole("link").first().click();
  await expect(page.getByTestId("event-detail")).toBeVisible({ timeout: 15_000 });

  const hyp = page.getByTestId("audience-hypothesis").first();
  await expect(hyp).toBeVisible({ timeout: 15_000 });
  await hyp.getByTestId("audience-feedback-correct").click();
  await expect(hyp.getByTestId("ai-feedback-current")).toContainText("correct", { timeout: 10_000 });

  const afterPut = await request.get(`${API}/events/${eventId}`, { headers: ADMIN });
  const persisted = (await afterPut.json()).audience.hypotheses[0].viewer_feedback;
  expect(persisted.state).toBe("correct");

  await page.getByTestId("audience-refresh").click();
  await expect(page.getByTestId("audience-hypothesis").first().getByTestId("ai-feedback-current")).toContainText(
    "correct",
    { timeout: 10_000 },
  );
});