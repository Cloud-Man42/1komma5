import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EvCharger } from "@/lib/api";

import {
  getActivePowerSegments,
  getChargerMaxPowerW,
  HaloPowerIndicator,
} from "./HaloPowerIndicator";

function charger(overrides: Partial<EvCharger> = {}): EvCharger {
  return {
    max_power_w: 11000,
    max_current_a: 16,
    nominal_voltage_v: 230,
    phases: 3,
    power_w: 5500,
    ...overrides,
  } as EvCharger;
}

describe("HaloPowerIndicator", () => {
  it("lights blocks in proportion to the delivered power", () => {
    render(<HaloPowerIndicator charger={charger()} />);

    expect(screen.getByRole("meter").getAttribute("aria-valuenow")).toBe("5500");
    expect(screen.getByText("5.5 kW")).toBeTruthy();
    expect(document.querySelectorAll(".halo-power-segment")).toHaveLength(12);
    expect(document.querySelectorAll(".halo-power-segment.is-active")).toHaveLength(6);
  });

  it("shows no illuminated blocks when actual power data is unavailable", () => {
    render(<HaloPowerIndicator charger={charger({ power_w: null })} />);

    expect(screen.getByRole("meter").hasAttribute("aria-valuenow")).toBe(false);
    expect(screen.getByRole("meter").getAttribute("aria-valuetext")).toBe("Ingen effektdata");
    expect(document.querySelectorAll(".halo-power-segment.is-active")).toHaveLength(0);
  });

  it("caps the display at all blocks and ignores negligible power", () => {
    expect(getActivePowerSegments(15000, 11000)).toBe(12);
    expect(getActivePowerSegments(24, 11000)).toBe(0);
    expect(getActivePowerSegments(-100, 11000)).toBe(0);
  });

  it("uses configured max power or derives it from the electrical limits", () => {
    expect(getChargerMaxPowerW(charger({ max_power_w: 7400 }))).toBe(7400);
    expect(getChargerMaxPowerW(charger({ max_power_w: null, phases: 1 }))).toBe(3680);
    expect(getChargerMaxPowerW(charger({ max_power_w: null, phases: 3 }))).toBeCloseTo(6373.95, 1);
  });
});
