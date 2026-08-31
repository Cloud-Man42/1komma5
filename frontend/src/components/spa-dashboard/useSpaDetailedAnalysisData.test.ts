import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useSpaDetailedAnalysisData } from "./useSpaDetailedAnalysisData";

const mockFetchSpaEnergyPeriod = vi.fn();
const mockFetchSpaEnergyBreakdown = vi.fn();
const mockFetchSpaEconomics = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSpaEnergyPeriod: (...args: unknown[]) => mockFetchSpaEnergyPeriod(...args),
  fetchSpaEnergyBreakdown: (...args: unknown[]) => mockFetchSpaEnergyBreakdown(...args),
  fetchSpaEconomics: (...args: unknown[]) => mockFetchSpaEconomics(...args),
}));

describe("useSpaDetailedAnalysisData", () => {
  beforeEach(() => {
    mockFetchSpaEnergyPeriod.mockReset();
    mockFetchSpaEnergyBreakdown.mockReset();
    mockFetchSpaEconomics.mockReset();
    mockFetchSpaEnergyPeriod.mockResolvedValue({ has_data: true, energy_kwh: 10 });
    mockFetchSpaEnergyBreakdown.mockResolvedValue({ rows: [], granularity: "day" });
    mockFetchSpaEconomics.mockResolvedValue({ energy_kwh: 10, cost_sek: 5, data_quality: "MEASURED" });
  });

  it("loads energy, breakdown and economics in one batched request", async () => {
    const { result } = renderHook(() => useSpaDetailedAnalysisData("akarp", "month"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockFetchSpaEnergyPeriod).toHaveBeenCalledTimes(1);
    expect(mockFetchSpaEnergyBreakdown).toHaveBeenCalledTimes(1);
    expect(mockFetchSpaEconomics).toHaveBeenCalledTimes(1);
    expect(mockFetchSpaEnergyPeriod).toHaveBeenCalledWith("akarp", "month");
    expect(mockFetchSpaEconomics).toHaveBeenCalledWith("akarp", "month");
    expect(result.current.energy).toEqual({ has_data: true, energy_kwh: 10 });
  });

  it("records breakdown errors without failing the whole hook", async () => {
    mockFetchSpaEnergyBreakdown.mockRejectedValue(new Error("API fel"));

    const { result } = renderHook(() => useSpaDetailedAnalysisData("akarp", "week"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.breakdownError).toBe("API fel");
    expect(result.current.energy).toEqual({ has_data: true, energy_kwh: 10 });
  });
});
