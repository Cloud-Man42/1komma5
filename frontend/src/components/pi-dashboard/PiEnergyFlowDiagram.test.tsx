import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PiEnergyFlowDiagram } from "./PiEnergyFlowDiagram";
import type { DisplayOverview } from "@/lib/displayOverview";

const mockData: DisplayOverview = {
  generated_at: "2026-08-29T08:00:00Z",
  site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
  freshness: { updated_at: "2026-08-29T08:00:00Z", data_age_seconds: 5, stale: false, connection_state: "CONNECTED" },
  live: {
    solar_power_kw: 3.25,
    house_power_kw: 1.78,
    grid_net_power_kw: 1.24,
    grid_direction: "export",
    grid_direction_sv: "Exporterar",
    battery_soc_pct: 58,
    battery_power_kw: 0.46,
    battery_state_sv: "Laddar",
    battery_stored_kwh: 7.8,
    battery_capacity_kwh: 13.5,
    solar_surplus_kw: 1.47,
    produced_today_kwh: 24.7,
    consumed_today_kwh: 16.3,
    imported_today_kwh: 0,
    exported_today_kwh: 8.1,
    self_consumption_pct: 87,
    self_sufficiency_pct: 81,
    battery_soh_pct: null,
  },
  sparklines: {},
  weather: { available: true, temperature_c: 18, label_sv: "Klart", icon: "☀" },
  price: { available: true, tier: "red", tier_label_sv: "Rött (dyrt)", current_ore_kwh: 200.6 },
  flow: {
    available: true,
    nodes: [
      { key: "solar", label_sv: "SOL", power_kw: 3.25 },
      { key: "battery", label_sv: "BATTERI", power_kw: 0.46, status_sv: "Laddar" },
      { key: "grid", label_sv: "NÄT", power_kw: 1.24, status_sv: "Exporterar" },
      { key: "house", label_sv: "HUS", power_kw: 1.78 },
      { key: "charger", label_sv: "LADDBOX", power_kw: 0, status_sv: "Väntar" },
      { key: "spa", label_sv: "SPA", power_kw: 0.6, status_sv: "Standby" },
    ],
  },
  vehicle: { available: true, status_sv: "Väntar på bil", soc_pct: 78, range_km: 412 },
  charger: { available: true, status_sv: "Väntar på bil", power_w: 0, available_current_a: 16 },
  spa: { available: true, water_temperature_c: 37.4, filter_status_sv: "Pågår" },
  economy: { available: true, total_savings_sek: 2846, total_cost_sek: 1924, net_sek: 912, daily: [] },
  highlights: { available: true, items: [{ label_sv: "Högsta soleffekt", value: "8,8 kW", detail_sv: "12:31" }] },
  system_status: { status_sv: "Allt normalt", detail_sv: "Alla system fungerar som de ska.", healthy: true },
};

describe("PiEnergyFlowDiagram", () => {
  it("renders flow nodes when data is available", () => {
    render(<PiEnergyFlowDiagram slug="preview" data={mockData} />);
    expect(screen.getByText("ENERGIFLÖDE – JUST NU")).toBeInTheDocument();
    expect(screen.getByText("SOL")).toBeInTheDocument();
    expect(screen.getByText("HUS")).toBeInTheDocument();
    expect(screen.getByText("LADDBOX")).toBeInTheDocument();
  });

  /*
   * The viewBox is drawn for the home card's box. Mapping it non-uniformly onto
   * a box of another shape — the detail view's is ~3x wider and squeezed
   * vertically — stretches the glyphs and drives each node's three text lines
   * into each other, so every such caller has to opt into uniform scaling.
   */
  it("maps the viewBox straight onto the home card, which is the authored box", () => {
    const { container } = render(<PiEnergyFlowDiagram slug="preview" data={mockData} />);
    expect(container.querySelector(".pi-flow-svg")?.getAttribute("preserveAspectRatio")).toBe(
      "none",
    );
  });

  it("scales uniformly and centres when told to fit a box of another shape", () => {
    const { container } = render(<PiEnergyFlowDiagram data={mockData} fit="contain" />);
    expect(container.querySelector(".pi-flow-svg")?.getAttribute("preserveAspectRatio")).toBe(
      "xMidYMid meet",
    );
  });

  it("shows missing state when flow unavailable", () => {
    render(
      <PiEnergyFlowDiagram
        slug="preview"
        data={{
          ...mockData,
          flow: { available: false, nodes: [] },
        }}
      />,
    );
    expect(screen.getByText("Data saknas")).toBeInTheDocument();
  });
});
