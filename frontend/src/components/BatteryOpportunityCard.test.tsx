import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BatteryOpportunityCard } from "./BatteryOpportunityCard";

const baseAdvice = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  available: true,
  monitor_only: true,
  unavailable_reason_sv: null,
  action: "STORE_IN_BATTERY",
  action_label_sv: "Spara i batteriet",
  headline_sv: "Spara i batteriet",
  reason_sv: "Spara överskott inför kvällstoppen.",
  confidence: 0.8,
  battery_soc_pct: 55,
  recommended_reserve_soc_pct: 30,
  expected_value_sek_kwh: 0.18,
  next_peak_at: "2026-03-01T18:00:00Z",
  next_peak_import_sek_kwh: 2.1,
  optimization_mode: "economic",
  strategy_state: "save_battery",
};

describe("BatteryOpportunityCard", () => {
  it("renders idash layout with headline, metrics and monitor badge", () => {
    render(<BatteryOpportunityCard advice={baseAdvice} />);
    expect(screen.getByTestId("battery-opportunity-card")).toHaveClass("idash-advisor-card");
    expect(screen.getByText("BATTERIRÅDGIVARE")).toBeInTheDocument();
    expect(screen.getByText("Spara i batteriet")).toBeInTheDocument();
    expect(screen.getByText(/Endast övervakning/i)).toBeInTheDocument();
    expect(screen.getByText("55 %")).toBeInTheDocument();
    expect(screen.getByText("80 %")).toBeInTheDocument();
    expect(screen.getByText(/Spara överskott inför kvällstoppen/i)).toBeInTheDocument();
  });

  it("renders peak timing when available", () => {
    render(<BatteryOpportunityCard advice={baseAdvice} />);
    expect(screen.getByText("Nästa pristopp")).toBeInTheDocument();
    expect(screen.getByText("Förväntat köp då")).toBeInTheDocument();
  });

  it("renders unavailable state", () => {
    render(
      <BatteryOpportunityCard
        advice={{
          ...baseAdvice,
          available: false,
          headline_sv: null,
          action_label_sv: null,
          unavailable_reason_sv: "Batterinivå (SOC) saknas.",
        }}
      />,
    );
    expect(screen.getByText("Batterinivå (SOC) saknas.")).toBeInTheDocument();
  });
});
