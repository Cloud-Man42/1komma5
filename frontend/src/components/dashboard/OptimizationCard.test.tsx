import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OptimizationCard } from "@/components/dashboard/OptimizationCard";

describe("OptimizationCard", () => {
  it("renders strategy, explanation and reasoning steps", () => {
    render(
      <OptimizationCard
        optimization={{
          strategy_sv: "Väntar på solel",
          explanation_sv: "Bilen behöver 18 kWh. EMIC reserverar solel.",
          reasoning_steps: [
            "Solel/export: PV 3.0 kW, nätexport 0.9 kW — solöverskott kan användas.",
            "Elprisnivå: grönt (billigt).",
            "EMIC-beslut: Väntar på solel (solar_forecast_wait).",
          ],
          reserved_solar_kwh: 12,
          planned_grid_kwh: 6,
          ev_need_kwh: 18,
          battery_soc_pct: 82,
        }}
      />,
    );

    expect(screen.getByText("Väntar på solel")).toBeTruthy();
    expect(screen.getByText(/Bilen behöver 18 kWh/)).toBeTruthy();
    expect(screen.getByText("Så resonerar EMIC")).toBeTruthy();
    expect(screen.getByTestId("optimization-reasoning-steps").querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Reserverad solel")).toBeTruthy();
    expect(screen.getByText("12,0 kWh")).toBeTruthy();
  });

  it("renders nothing when optimization is null", () => {
    const { container } = render(<OptimizationCard optimization={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("omits reasoning block when steps are empty", () => {
    render(
      <OptimizationCard
        optimization={{
          strategy_sv: "Ingen SmartLaddning aktiv",
          explanation_sv: "Aktivera bridge under Konfiguration.",
          reasoning_steps: [],
          reserved_solar_kwh: null,
          planned_grid_kwh: null,
          ev_need_kwh: null,
          battery_soc_pct: null,
        }}
      />,
    );

    expect(screen.queryByText("Så resonerar EMIC")).toBeNull();
    expect(screen.getByText("Ingen SmartLaddning aktiv")).toBeTruthy();
  });
});
