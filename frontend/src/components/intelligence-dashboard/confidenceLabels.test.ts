import { describe, expect, it } from "vitest";
import {
  confidenceHeadlineSv,
  confidenceTierSv,
  forecastConfidencePct,
  shouldShowModelCalibration,
} from "./confidenceLabels";

describe("confidenceLabels", () => {
  it("uses forecast run confidence, not model calibration score", () => {
    expect(
      forecastConfidencePct({
        site_id: 1,
        generated_at: "2026-08-27T08:00:00Z",
        model_version: "solar-forecast-v2",
        quality: "MEDIUM",
        weather_source: "live",
        expected_today_kwh: 20,
        remaining_today_kwh: 10,
        peak_power_w: 3000,
        confidence: 0.6065,
        lower_today_kwh: 10,
        upper_today_kwh: 30,
        weather_summary: "Klart",
        confidence_score: 14.4,
        confidence_label: "Low",
        model_state: "PRELIMINARY",
        historical_samples: 12,
      }),
    ).toBe(61);
  });

  it("maps forecast confidence to Swedish tiers", () => {
    expect(confidenceTierSv(61)).toBe("Medel");
    expect(confidenceHeadlineSv(61)).toBe("Medel tilltro");
    expect(confidenceTierSv(14)).toBe("Låg");
  });

  it("shows model calibration only while model is immature", () => {
    expect(
      shouldShowModelCalibration({
        site_id: 1,
        generated_at: "2026-08-27T08:00:00Z",
        model_version: "solar-forecast-v2",
        quality: "MEDIUM",
        weather_source: "live",
        expected_today_kwh: 20,
        remaining_today_kwh: 10,
        peak_power_w: 3000,
        confidence: 0.6,
        lower_today_kwh: 10,
        upper_today_kwh: 30,
        weather_summary: "Klart",
        confidence_score: 14,
        model_state: "PRELIMINARY",
      }),
    ).toBe(true);
    expect(
      shouldShowModelCalibration({
        site_id: 1,
        generated_at: "2026-08-27T08:00:00Z",
        model_version: "solar-forecast-v2",
        quality: "HIGH",
        weather_source: "live",
        expected_today_kwh: 20,
        remaining_today_kwh: 10,
        peak_power_w: 3000,
        confidence: 0.9,
        lower_today_kwh: 10,
        upper_today_kwh: 30,
        weather_summary: "Klart",
        confidence_score: 82,
        model_state: "MATURE",
      }),
    ).toBe(false);
  });
});
