import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mergeChartData } from "@/components/EnergyChart";
import { makeReading } from "@/test/fixtures";

describe("mergeChartData", () => {
  it("merges readings with forecast bounds", () => {
    const rows = mergeChartData(
      [makeReading({ recorded_at: "2026-08-18T10:00:00Z", solar_production_w: 5000 })],
      [
        {
          timestamp: "2026-08-18T10:00:00Z",
          baseline_power_w: 4000,
          corrected_power_w: 4200,
          expected_energy_kwh: 1.0,
          lower_bound_power_w: 3500,
          upper_bound_power_w: 4800,
          confidence: 0.9,
        },
      ],
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].solar).toBe(5000);
    expect(rows[0].forecastSolar).toBe(4200);
    expect(rows[0].forecastLower).toBe(3500);
    expect(rows[0].forecastUpper).toBe(4800);
  });

  it("returns empty array for no readings and no forecast", () => {
    expect(mergeChartData([], [])).toEqual([]);
  });

  it("adds forecast-only rows when readings are missing", () => {
    const rows = mergeChartData([], [
      {
        timestamp: "2026-08-18T11:00:00Z",
        baseline_power_w: 3000,
        corrected_power_w: 3100,
        expected_energy_kwh: 0.75,
        lower_bound_power_w: 2500,
        upper_bound_power_w: 3600,
        confidence: 0.8,
      },
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0].solar).toBeNull();
    expect(rows[0].forecastSolar).toBe(3100);
  });
});

describe("EnergyChart component", () => {
  it("shows empty message without readings", async () => {
    const { EnergyChart } = await import("@/components/EnergyChart");
    render(<EnergyChart readings={[]} />);
    expect(screen.getByText("Ingen historisk data ännu.")).toBeTruthy();
  });
});
