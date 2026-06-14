import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

vi.mock("@/api/campaigns", () => ({
  listCampaigns: vi.fn().mockResolvedValue([]),
  getCampaign: vi.fn(),
  createCampaign: vi.fn(),
}));

describe("App shell", () => {
  it("renders campaign list route", async () => {
    render(
      <MemoryRouter initialEntries={["/campaigns"]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("campaign-list")).toBeInTheDocument();
  });
});