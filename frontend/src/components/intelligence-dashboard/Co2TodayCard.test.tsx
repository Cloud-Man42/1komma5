import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Co2TodayCard } from "./Co2TodayCard";

describe("Co2TodayCard", () => {
  it("shows dash when no production", () => {
    render(<Co2TodayCard today={null} />);
    expect(screen.getByTestId("co2-today-card")).toHaveTextContent("—");
  });

  it("shows estimated co2 for produced kwh", () => {
    render(
      <Co2TodayCard
        today={{
          produced_kwh: 10,
          consumed_kwh: 0,
          imported_kwh: 0,
          exported_kwh: 0,
          energy_cost_sek: 0,
          savings_sek: 0,
          stale: false,
        }}
      />,
    );
    expect(screen.getByTestId("co2-today-card")).toHaveTextContent("450 g");
  });
});
