import { describe, expect, it } from "vitest";
import {
  computeCo2SavedKg,
  formatEvDuration,
  modeLabel,
  sessionSourceLabel,
  buildPowerChartFromHistory,
} from "./evDashboardHelpers";
import { evSectionHref, parseEvSection } from "./evSection";

describe("evSection", () => {
  it("parses hash sections", () => {
    expect(parseEvSection("#historik")).toBe("history");
    expect(parseEvSection("")).toBe("overview");
  });

  it("builds hrefs", () => {
    expect(evSectionHref("akarp", "overview")).toBe("/sites/akarp/ev");
    expect(evSectionHref("akarp", "charging")).toBe("/sites/akarp/ev#laddning");
  });
});

describe("evDashboardHelpers", () => {
  it("labels charging modes", () => {
    expect(modeLabel("SMART_CHARGE")).toBe("Smart laddning");
  });

  it("formats session duration", () => {
    expect(formatEvDuration("2026-08-24T08:00:00Z", "2026-08-24T09:30:00Z")).toBe("1 h 30 min");
  });

  it("builds power chart from balance history", () => {
    const chart = buildPowerChartFromHistory([
      {
        charger_id: 1,
        recorded_at: "2026-08-24T08:00:00Z",
        status: "ok",
        flags: [],
        inverter_display_name: "Sungrow",
        sungrow_pv_power_w: 0,
        sungrow_load_power_w: 0,
        sungrow_grid_import_w: 0,
        sungrow_grid_export_w: 0,
        sungrow_battery_charge_w: 0,
        sungrow_battery_discharge_w: 0,
        sungrow_battery_soc_pct: 0,
        sungrow_fresh: true,
        sungrow_telemetry_age_seconds: 0,
        halo_power_w: 7200,
        virtual_evse_reported_power_w: null,
        heartbeat_observed_ev_power_w: null,
        heartbeat_home_consumption_w: null,
        non_ev_house_load_w: null,
        non_ev_house_load_reason: null,
        residual_w: null,
        alignment_delta_seconds: null,
        energy_flow_line: null,
      },
    ]);
    expect(chart[0].powerKw).toBe(7.2);
  });

  it("computes co2 savings from month stats", () => {
    const kg = computeCo2SavedKg({
      period: "month",
      period_from: "2026-08-01",
      period_to: "2026-08-31",
      total_energy_kwh: 100,
      actual_cost_sek: 20,
      reference_cost_sek: 80,
      savings_sek: 60,
      average_cost_sek_per_kwh: 0.2,
      energy_sources: {
        solar_direct_kwh: 50,
        solar_battery_kwh: 10,
        grid_battery_kwh: 5,
        grid_direct_kwh: 35,
      },
      renewable_share_percent: 60,
      grid_share_percent: 40,
      smart_charging_savings_sek: 60,
      solar_contribution_sek: 10,
      session_count: 12,
      savings_baseline: "immediate",
    });
    expect(kg).toBeGreaterThan(0);
  });

  it("labels session energy source", () => {
    const label = sessionSourceLabel({
      id: 1,
      charger_id: 1,
      started_at: "2026-08-24T08:00:00Z",
      ended_at: "2026-08-24T10:00:00Z",
      status: "completed",
      total_energy_kwh: 10,
      energy_sources: {
        solar_direct_kwh: 10,
        solar_battery_kwh: 0,
        grid_battery_kwh: 0,
        grid_direct_kwh: 0,
      },
      actual_cost_sek: 0,
      reference_cost_sek: 0,
      savings_sek: 0,
      smart_charging_savings_sek: 0,
      solar_contribution_sek: 0,
      renewable_share_pct: 100,
      grid_share_pct: 0,
      average_cost_sek_per_kwh: 0,
      energy_quality: "good",
      cost_quality: "good",
      attribution_quality: "good",
      savings_baseline: "immediate",
      calculation_version: "1",
      reconciliation_delta_kwh: 0,
      intervals: [],
    });
    expect(label.label).toBe("Sol");
  });
});
