import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HeartbeatAuditPanel } from "./HeartbeatAuditPanel";
import type { HeartbeatAuditDaily } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchHeartbeatAuditToday: vi.fn(),
}));

import { fetchHeartbeatAuditToday } from "@/lib/api";

const sample: HeartbeatAuditDaily = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  day: "2026-09-02",
  rollup: {
    actual_energy_cost_sek: 42.5,
    baseline_cost_without_optimization_sek: 58.0,
    heartbeat_saving_sek: 15.5,
    emic_theoretical_optimal_cost_sek: 38.0,
    additional_optimization_potential_sek: 4.5,
    heartbeat_efficiency_pct: 34.4,
    imported_kwh: 12.3,
    exported_kwh: 1.1,
  },
  solar_self_consumed_kwh: 5.0,
  battery_self_consumed_kwh: 2.0,
  period_count: 24,
  periods: [
    {
      period_start: "2026-09-02T08:00:00Z",
      period_end: "2026-09-02T08:15:00Z",
      import_price_sek_kwh: 1.21,
      export_price_sek_kwh: 0.39,
      grid_import_w: 1200,
      grid_export_w: 0,
      battery_soc_pct: 70,
      ev_power_w: 0,
      heartbeat_mode: "SMART_CHARGE",
      ai_decision: "charge_cheap",
      heartbeat_reason: "Cheap window",
      emic_strategy_state: "CHARGE_VEHICLE",
      emic_recommended_action: "USE_NOW",
    },
  ],
};

describe("HeartbeatAuditPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(fetchHeartbeatAuditToday).mockReturnValue(new Promise(() => {}));
    render(<HeartbeatAuditPanel siteSlug="akarp" />);
    expect(screen.getByText(/Hämtar auditdata/i)).toBeInTheDocument();
  });

  it("renders rollup metrics and efficiency", async () => {
    vi.mocked(fetchHeartbeatAuditToday).mockResolvedValue(sample);
    render(<HeartbeatAuditPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("heartbeat-efficiency")).toHaveTextContent("34.4 %");
    expect(screen.getByText("42.50 kr")).toBeInTheDocument();
    expect(screen.getByText("SMART_CHARGE")).toBeInTheDocument();
  });

  it("shows empty message on fetch error", async () => {
    vi.mocked(fetchHeartbeatAuditToday).mockRejectedValue(new Error("503"));
    render(<HeartbeatAuditPanel siteSlug="akarp" />);
    expect(await screen.findByText(/Auditdata otillgänglig/i)).toBeInTheDocument();
  });
});
