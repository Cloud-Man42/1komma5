import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EnergyFlowDiagram } from "./EnergyFlowDiagram";

const reading = {
  recorded_at: "2026-08-13T18:00:00Z",
  solar_production_w: 3200,
  consumption_w: 1800,
  grid_import_w: 0,
  grid_export_w: 900,
  battery_soc_pct: 72,
  battery_power_w: 500,
};

describe("EnergyFlowDiagram", () => {
  it("renders four analog power gauges in full mode", () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    expect(screen.getByLabelText("Energiflöde visualisering")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Solenergi" })).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Hushåll" })).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Batteri" })).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Nät" })).toBeInTheDocument();
  });

  it("does not render house photo scene", () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    expect(document.querySelector(".energy-flow-photo-img")).toBeNull();
    expect(document.querySelector(".energy-wire-flow-glow")).toBeNull();
  });

  it("renders compact gauge panel", () => {
    render(<EnergyFlowDiagram reading={reading} size="compact" />);
    expect(screen.getByText("Solenergi")).toBeInTheDocument();
    expect(screen.getByText("Hushåll")).toBeInTheDocument();
  });

  it("shows active flow notes when power is moving", () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    expect(screen.getByText(/Sol → hus/)).toBeInTheDocument();
  });
});
