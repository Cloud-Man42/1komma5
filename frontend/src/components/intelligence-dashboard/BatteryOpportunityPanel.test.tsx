import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { BatteryOpportunityPanel } from "./BatteryOpportunityPanel";

const mockFetchBatteryOpportunity = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchBatteryOpportunity: (...args: unknown[]) => mockFetchBatteryOpportunity(...args),
}));

describe("BatteryOpportunityPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state with idash styling", () => {
    mockFetchBatteryOpportunity.mockReturnValue(new Promise(() => undefined));
    render(<BatteryOpportunityPanel slug="akarp" />);
    expect(screen.getByTestId("battery-opportunity-panel")).toHaveClass("idash-advisor-card");
    expect(screen.getByText(/Hämtar batteriråd/i)).toBeInTheDocument();
  });

  it("renders card when data loads", async () => {
    mockFetchBatteryOpportunity.mockResolvedValue({
      slug: "akarp",
      timezone: "Europe/Stockholm",
      available: true,
      monitor_only: true,
      unavailable_reason_sv: null,
      action: "STORE_IN_BATTERY",
      action_label_sv: "Spara i batteriet",
      headline_sv: "Spara i batteriet",
      reason_sv: "Test",
      confidence: 0.8,
      battery_soc_pct: 55,
      recommended_reserve_soc_pct: 30,
      expected_value_sek_kwh: 0.18,
      next_peak_at: null,
      next_peak_import_sek_kwh: null,
      optimization_mode: null,
      strategy_state: null,
    });
    render(<BatteryOpportunityPanel slug="akarp" />);
    expect(await screen.findByTestId("battery-opportunity-card")).toBeInTheDocument();
  });
});
