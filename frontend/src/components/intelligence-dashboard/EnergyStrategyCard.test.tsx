import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnergyStrategyCard } from "./EnergyStrategyCard";
import type { EnergyStrategyCurrent } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchEnergyStrategyCurrent: vi.fn(),
}));

import { fetchEnergyStrategyCurrent } from "@/lib/api";

const sample: EnergyStrategyCurrent = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  period_start: "2026-08-13T11:00:00Z",
  market_price_sek_kwh: 0.32,
  import_price_sek_kwh: 1.21,
  export_price_sek_kwh: 0.39,
  market_quality: "REAL",
  import_quality: "REAL",
  export_quality: "CALCULATED",
  battery_soc_pct: 74,
  strategy_state: "PEAK_AHEAD",
  confidence: 0.55,
  reason: "Peak ahead",
  reason_sv: "Högre importpris väntas senare.",
  next_peak_at: "2026-08-13T17:00:00Z",
  next_peak_import_sek_kwh: 3.16,
  optimization_mode: "MONITOR_ONLY",
  expected_saving_today_sek: 31.42,
  recommended_reserve_soc_pct: 58,
  recommended_action: "STORE_IN_BATTERY",
  eov_value_sek_kwh: 0.12,
  grid_surcharge_sek_kwh: 0.89,
  fuse_headroom_a: null,
  fuse_utilization_pct: null,
  ev_recommendations: [],
};

describe("EnergyStrategyCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockReturnValue(new Promise(() => {}));
    render(<EnergyStrategyCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(screen.getByText(/Hämtar strategidata/i)).toBeInTheDocument();
  });

  it("renders three price lines and strategy state", async () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockResolvedValue(sample);
    render(<EnergyStrategyCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(await screen.findByText("SPARA ENERGI")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "EMIC ENERGY STRATEGY" })).toBeInTheDocument();
    expect(screen.getByText("32 öre")).toBeInTheDocument();
    expect(screen.getByText("121 öre")).toBeInTheDocument();
    expect(screen.getByText("39 öre")).toBeInTheDocument();
    expect(screen.getByText(/74 %/)).toBeInTheDocument();
    expect(screen.getByText(/31\.42 SEK/)).toBeInTheDocument();
    expect(screen.getByTestId("strategy-grid-surcharge")).toHaveTextContent("89 öre");
  });

  it("shows peak protection banner", async () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockResolvedValue({
      ...sample,
      strategy_state: "PEAK_PROTECTION",
      fuse_headroom_a: 1.5,
      fuse_utilization_pct: 92,
      reason_sv: "Huvudsäkring nära max",
    });
    render(<EnergyStrategyCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(await screen.findByTestId("strategy-peak-banner")).toHaveTextContent("92%");
    expect(screen.getByText("TOPPSKYDD")).toBeInTheDocument();
  });

  it("shows EV recommendations", async () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockResolvedValue({
      ...sample,
      strategy_state: "CHARGE_VEHICLE",
      ev_recommendations: [
        {
          charger_id: 7,
          charger_name: "Halo",
          window_start: "2026-08-13T22:00:00Z",
          window_end: "2026-08-13T23:00:00Z",
          avg_import_sek_kwh: 0.55,
          current_import_sek_kwh: 1.21,
          estimated_saving_sek: 6.6,
          reason_sv: "Billigare fönster",
        },
      ],
    });
    render(<EnergyStrategyCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(await screen.findByTestId("strategy-ev-recommendations")).toHaveTextContent("Halo");
    expect(screen.getByText("LADDA FORDON")).toBeInTheDocument();
  });

  it("shows empty message on fetch error", async () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockRejectedValue(new Error("503"));
    render(<EnergyStrategyCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(await screen.findByText(/Strategidata otillgänglig/i)).toBeInTheDocument();
  });
});
