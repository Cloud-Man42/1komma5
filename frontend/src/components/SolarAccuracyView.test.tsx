import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SolarAccuracyView } from "@/components/SolarAccuracyView";

const mockFetchSolarAccuracy = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSolarAccuracy: (...args: unknown[]) => mockFetchSolarAccuracy(...args),
}));

describe("SolarAccuracyView", () => {
  it("renders learning state when no history", async () => {
    mockFetchSolarAccuracy.mockResolvedValueOnce({
      site_slug: "akarp",
      model_version: "solar-forecast-v2",
      model_state: "NO_DATA",
      mape_7d_pct: null,
      mape_30d_pct: null,
      mape_7d_valid_days: 0,
      mape_30d_valid_days: 0,
      mae_kwh_7d: null,
      mae_kwh_30d: null,
      bias_pct_30d: null,
      sample_count_30d: 0,
      historical_samples: 0,
      production_days_observed: 12,
      correction_factor: 1,
      confidence_score: null,
      confidence_label: null,
      metrics_insufficient: true,
      raw_mae_30d: null,
      corrected_mae_30d: null,
      improvement_pct_30d: null,
      min_samples_for_calibrated: 30,
    });
    render(<SolarAccuracyView siteSlug="akarp" />);
    expect(await screen.findByText("Modellkvalitet")).toBeTruthy();
    expect(screen.getByText(/Prognosmodellen lär sig/)).toBeTruthy();
    expect(screen.getByText(/12 dagar med mätdata/i)).toBeTruthy();
  });

  it("renders calibrated metrics", async () => {
    mockFetchSolarAccuracy.mockResolvedValueOnce({
      site_slug: "akarp",
      model_version: "solar-forecast-v2",
      model_state: "CALIBRATED",
      mape_7d_pct: 10.5,
      mape_30d_pct: 12.0,
      mape_7d_valid_days: 6,
      mape_30d_valid_days: 28,
      mae_kwh_7d: 1.0,
      mae_kwh_30d: 1.1,
      bias_pct_30d: -2.0,
      sample_count_30d: 38,
      historical_samples: 38,
      production_days_observed: 38,
      correction_factor: 0.937,
      confidence_score: 81,
      confidence_label: "High",
      metrics_insufficient: false,
      raw_mae_30d: 3.8,
      corrected_mae_30d: 2.6,
      improvement_pct_30d: 31.6,
      min_samples_for_calibrated: 30,
    });
    render(<SolarAccuracyView siteSlug="akarp" />);
    expect(await screen.findByText("Modellkvalitet")).toBeTruthy();
    expect(screen.getByText("10.5 %")).toBeTruthy();
    expect(screen.getByText("solar-forecast-v2")).toBeTruthy();
  });

  it("returns null on fetch error", async () => {
    mockFetchSolarAccuracy.mockRejectedValueOnce(new Error("Failed"));
    const { container } = render(<SolarAccuracyView siteSlug="akarp" />);
    await screen.findByText("Laddar modellkvalitet…");
    await vi.waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});
