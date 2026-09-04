import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { ForecastLearningLoopCard } from "./ForecastLearningLoopCard";

describe("ForecastLearningLoopCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("combines learning summary and solar correction", async () => {
    vi.spyOn(api, "fetchForecastLearningSummary").mockResolvedValue({
      slug: "akarp",
      timezone: "Europe/Stockholm",
      days: 7,
      metrics: [{ kind: "solar_w", mae: 120, bias: 800, sample_count: 14, mape_pct: null }],
      last_reconciled_at: "2026-09-04T06:00:00Z",
    });
    vi.spyOn(api, "fetchSolarAccuracy").mockResolvedValue({
      site_slug: "akarp",
      model_version: "v1",
      model_state: "OK",
      mape_7d_pct: null,
      mape_30d_pct: null,
      mape_7d_valid_days: 0,
      mape_30d_valid_days: 0,
      mae_kwh_7d: null,
      mae_kwh_30d: null,
      bias_pct_30d: null,
      sample_count_30d: 0,
      historical_samples: 0,
      production_days_observed: 0,
      correction_factor: 0.92,
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
    render(<ForecastLearningLoopCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText("0.920×")).toBeInTheDocument();
    });
    expect(screen.getByText("+800 W")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("shows error when either fetch fails", async () => {
    vi.spyOn(api, "fetchForecastLearningSummary").mockRejectedValue(new Error("fail"));
    render(<ForecastLearningLoopCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText(/fail/)).toBeInTheDocument();
    });
  });
});
