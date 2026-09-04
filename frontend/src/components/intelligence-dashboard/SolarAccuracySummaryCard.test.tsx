import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { SolarAccuracySummaryCard } from "./SolarAccuracySummaryCard";

describe("SolarAccuracySummaryCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders accuracy metrics", async () => {
    vi.spyOn(api, "fetchSolarAccuracy").mockResolvedValue({
      site_slug: "akarp",
      model_version: "v1",
      model_state: "OK",
      mape_7d_pct: 12.3,
      mape_30d_pct: null,
      mape_7d_valid_days: 7,
      mape_30d_valid_days: 0,
      mae_kwh_7d: null,
      mae_kwh_30d: null,
      bias_pct_30d: -1.2,
      sample_count_30d: 30,
      historical_samples: 100,
      production_days_observed: 30,
      correction_factor: 0.95,
      confidence_score: null,
      confidence_label: null,
      metrics_insufficient: false,
      raw_mae_30d: null,
      corrected_mae_30d: null,
      improvement_pct_30d: null,
      wape_7d_pct: null,
      wape_30d_pct: null,
      rmse_kwh_7d: null,
      rmse_kwh_30d: null,
      r2_30d: null,
      insufficient_reason: null,
    });
    render(<SolarAccuracySummaryCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText("12.3 %")).toBeInTheDocument();
    });
    expect(screen.getByText("-1.2 %")).toBeInTheDocument();
    expect(screen.getByText("0.950×")).toBeInTheDocument();
  });

  it("shows error on fetch failure", async () => {
    vi.spyOn(api, "fetchSolarAccuracy").mockRejectedValue(new Error("503"));
    render(<SolarAccuracySummaryCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText(/503/)).toBeInTheDocument();
    });
  });
});
