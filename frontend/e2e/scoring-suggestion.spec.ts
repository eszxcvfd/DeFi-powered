import { test, expect } from "@playwright/test";

const API = "http://127.0.0.1:8000";
const ADMIN = { "X-Actor-Role": "admin" };

async function seedCopilotNotHelpful(request: import("@playwright/test").APIRequestContext, campaignId: string) {
  for (let i = 0; i < 2; i++) {
    const resp = await request.post(`${API}/campaigns/${campaignId}/discovery-copilot:respond`, {
      headers: { ...ADMIN, "Content-Type": "application/json" },
      data: { question: `What discovery scope fits this campaign (pass ${i})?` },
    });
    expect(resp.ok()).toBeTruthy();
    const rid = (await resp.json()).id as string;
    const fb = await request.put(`${API}/discovery-copilot-responses/${rid}/feedback`, {
      headers: { ...ADMIN, "Content-Type": "application/json" },
      data: { state: "not_helpful", reason_code: "weak_usefulness" },
    });
    expect(fb.ok()).toBeTruthy();
  }
}

test("generate scoring suggestion from feedback; weights change only on approve", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  await page.setExtraHTTPHeaders(ADMIN);

  const camp = await request.post(`${API}/campaigns`, {
    headers: { ...ADMIN, "Content-Type": "application/json" },
    data: {
      name: `Scoring Suggest ${Date.now()}`,
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

  await seedCopilotNotHelpful(request, campaignId);

  const before = await request.get(`${API}/campaigns/${campaignId}`, { headers: ADMIN });
  const weightsBefore = (await before.json()).scoring_weights as Record<string, number>;

  await page.goto(`/campaigns/${campaignId}`);
  await expect(page.getByTestId("campaign-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("scoring-suggestion-panel")).toBeVisible();

  await page.getByTestId("scoring-suggestion-generate").click();
  await expect(page.getByTestId("scoring-suggestion-review")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("scoring-suggestion-status")).toContainText(/pending review/i);

  const mid = await request.get(`${API}/campaigns/${campaignId}`, { headers: ADMIN });
  expect((await mid.json()).scoring_weights).toEqual(weightsBefore);

  await page.getByTestId("scoring-suggestion-reject").click();
  await expect(page.getByTestId("scoring-suggestion-empty")).toBeVisible({ timeout: 10_000 });

  const afterReject = await request.get(`${API}/campaigns/${campaignId}`, { headers: ADMIN });
  expect((await afterReject.json()).scoring_weights).toEqual(weightsBefore);

  const regen = await request.post(`${API}/campaigns/${campaignId}/scoring-suggestions:generate`, {
    headers: { ...ADMIN, "Content-Type": "application/json" },
  });
  expect(regen.ok()).toBeTruthy();
  const suggestionId = (await regen.json()).id as string;

  await page.reload();
  await expect(page.getByTestId("scoring-suggestion-approve")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("scoring-suggestion-approve").click();
  await expect(page.getByTestId("scoring-suggestion-empty")).toBeVisible({ timeout: 15_000 });

  const after = await request.get(`${API}/campaigns/${campaignId}`, { headers: ADMIN });
  expect((await after.json()).scoring_weights).not.toEqual(weightsBefore);

  const list = await request.get(`${API}/campaigns/${campaignId}/scoring-suggestions`, {
    headers: ADMIN,
  });
  const sets = (await list.json()) as { id: string; status: string }[];
  expect(sets.some((s) => s.id === suggestionId && s.status === "approved")).toBeTruthy();
  expect(sets.some((s) => s.status === "rejected")).toBeTruthy();
});