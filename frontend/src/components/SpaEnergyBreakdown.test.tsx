import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SpaEnergyBreakdown } from "@/components/SpaEnergyBreakdown";

const mockFetchSpaEnergyBreakdown = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSpaEnergyBreakdown: (...args: unknown[]) => mockFetchSpaEnergyBreakdown(...args),
  };
});

describe("SpaEnergyBreakdown", () => {
  beforeEach(() => {
    mockFetchSpaEnergyBreakdown.mockReset();
  });

  it("shows empty state when no rows", async () => {
    mockFetchSpaEnergyBreakdown.mockResolvedValue({
      period: "month",
      granularity: "day",
      rows: [],
      total: { has_data: false, energy_kwh: 0, solar_kwh: 0, battery_kwh: 0, grid_kwh: 0, grid_cost_sek: 0, solar_value_sek: 0, battery_value_sek: 0 },
    });
    render(<SpaEnergyBreakdown siteSlug="akarp" period="month" />);
    await waitFor(() => {
      expect(screen.getByText(/Ingen daglig energidata/i)).toBeInTheDocument();
    });
  });

  it("renders daily rows with cost split", async () => {
    mockFetchSpaEnergyBreakdown.mockResolvedValue({
      period: "month",
      granularity: "day",
      rows: [
        {
          period_start: "2026-08-24T22:00:00Z",
          period_label: "2026-08-25",
          energy_kwh: 2.0,
          solar_kwh: 1.0,
          battery_kwh: 0.5,
          grid_kwh: 0.5,
          grid_cost_sek: 1.0,
          solar_value_sek: 1.0,
          battery_value_sek: 0.5,
          savings_sek: 3.0,
        },
      ],
      total: {
        has_data: true,
        energy_kwh: 2.0,
        solar_kwh: 1.0,
        battery_kwh: 0.5,
        grid_kwh: 0.5,
        grid_cost_sek: 1.0,
        solar_value_sek: 1.0,
        battery_value_sek: 0.5,
      },
    });
    render(<SpaEnergyBreakdown siteSlug="akarp" period="month" />);
    await waitFor(() => {
      expect(screen.getByTestId("spa-energy-breakdown")).toBeInTheDocument();
    });
    expect(screen.getByText("2026-08-25")).toBeInTheDocument();
    expect(screen.getByText("Kostnad köpt el")).toBeInTheDocument();
    expect(screen.getByText("Totalt")).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    mockFetchSpaEnergyBreakdown.mockRejectedValue(new Error("API fel"));
    render(<SpaEnergyBreakdown siteSlug="akarp" period="month" />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("API fel");
    });
  });
});
