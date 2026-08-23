import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OptimizationCard } from "@/components/dashboard/OptimizationCard";

describe("OptimizationCard", () => {
  it("renders strategy, explanation and reasoning steps", () => {
    render(
      <OptimizationCard
        optimization={{
          strategy_sv: "Väntar på solel",
          explanation_sv: "Solöverskott väntas 10:00–15:00 innan deadline.",
          reasoning_steps: [
            "Solel/export: PV 3.0 kW, nätexport 0.9 kW — solöverskott kan användas.",
            "Elprisnivå: grönt (billigt).",
            "EMIC-beslut: Väntar på solel (solar_forecast_wait).",
          ],
          solar_first: true,
          battery_soc_pct: 82,
        }}
      />,
    );

    expect(screen.getByText("Väntar på solel")).toBeTruthy();
    expect(screen.getByText(/Solöverskott väntas 10:00–15:00/)).toBeTruthy();
    expect(screen.getByText("Så resonerar EMIC")).toBeTruthy();
    expect(screen.getByTestId("optimization-reasoning-steps").querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Energikälla")).toBeTruthy();
    expect(screen.getByText("Solel först")).toBeTruthy();
  });

  it("shows grid priority when little solar is expected", () => {
    render(
      <OptimizationCard
        optimization={{
          strategy_sv: "Laddar från nätet",
          explanation_sv: null,
          reasoning_steps: [],
          solar_first: false,
          battery_soc_pct: null,
        }}
      />,
    );

    expect(screen.getByText("Nät vid billiga timmar")).toBeTruthy();
  });

  it("omits the energy source row without a solar plan", () => {
    render(
      <OptimizationCard
        optimization={{
          strategy_sv: "Smart laddning aktiv",
          explanation_sv: null,
          reasoning_steps: [],
          solar_first: null,
          battery_soc_pct: 40,
        }}
      />,
    );

    expect(screen.queryByText("Energikälla")).toBeNull();
    expect(screen.getByText("Batteri")).toBeTruthy();
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
          solar_first: null,
          battery_soc_pct: null,
        }}
      />,
    );

    expect(screen.queryByText("Så resonerar EMIC")).toBeNull();
    expect(screen.getByText("Ingen SmartLaddning aktiv")).toBeTruthy();
  });
});
