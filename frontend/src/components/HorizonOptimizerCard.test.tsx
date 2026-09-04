import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HorizonOptimizerCard } from "./HorizonOptimizerCard";

const basePlan = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  available: true,
  monitor_only: true,
  unavailable_reason_sv: null,
  horizon_hours: 48,
  horizon_blocks: 96,
  generated_at: "2026-09-04T08:00:00Z",
  total_planned_savings_sek: 5.5,
  headline_sv: "Koordinerad 48h-plan för 1 laster",
  summary_sv: "Beräknad besparing: 5.50 kr.",
  loads: [
    {
      load_id: "ev_charger_1",
      name: "Garage EV",
      load_type: "ev",
      priority: 60,
      strategy: "SMART",
      window_start: "2026-09-04T10:00:00Z",
      window_end: "2026-09-04T12:00:00Z",
      expected_energy_kwh: 6,
      expected_cost_sek: 12,
      expected_energy_source: "SOLAR",
      savings_sek: 5.5,
      reason_sv: "smart",
      explanation_sv: "Billigt fönster",
    },
  ],
  battery: {
    slug: "akarp",
    timezone: "Europe/Stockholm",
    available: true,
    monitor_only: true,
    unavailable_reason_sv: null,
    action: "STORE_IN_BATTERY",
    action_label_sv: "Spara i batteriet",
    headline_sv: "Spara i batteriet",
    reason_sv: "Spara överskott.",
    confidence: 0.8,
    battery_soc_pct: 55,
    recommended_reserve_soc_pct: 30,
    expected_value_sek_kwh: 0.18,
    next_peak_at: null,
    next_peak_import_sek_kwh: null,
    optimization_mode: "MONITOR_ONLY",
    strategy_state: "SAVE_BATTERY",
  },
};

describe("HorizonOptimizerCard", () => {
  it("renders headline, load plan and monitor-only badge", () => {
    render(<HorizonOptimizerCard plan={basePlan} />);
    expect(screen.getByText("Horizon Optimizer")).toBeInTheDocument();
    expect(screen.getByText("Koordinerad 48h-plan för 1 laster")).toBeInTheDocument();
    expect(screen.getByText("Garage EV")).toBeInTheDocument();
    expect(screen.getByText(/Endast övervakning/i)).toBeInTheDocument();
    expect(screen.getByText("Spara i batteriet")).toBeInTheDocument();
  });

  it("renders unavailable state", () => {
    render(
      <HorizonOptimizerCard
        plan={{
          ...basePlan,
          available: false,
          loads: [],
          headline_sv: null,
          summary_sv: null,
          unavailable_reason_sv: "Inga flexibla laster är konfigurerade.",
          battery: null,
        }}
      />,
    );
    expect(screen.getByText("Inga flexibla laster är konfigurerade.")).toBeInTheDocument();
  });
});
