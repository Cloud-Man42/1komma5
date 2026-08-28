import { describe, expect, it } from "vitest";
import {
  buildEnergyBalance,
  buildFlowChartSeries,
  buildLiveMetrics,
  buildTodayMetrics,
  integrateBatteryKwh,
  peakSummary,
} from "./energyDashboardHelpers";
import { energySectionHref, parseEnergySection } from "./energySection";

describe("energySection", () => {
  it("parses hash sections", () => {
    expect(parseEnergySection("#historik")).toBe("history");
    expect(parseEnergySection("")).toBe("flow");
    expect(parseEnergySection("#toppar")).toBe("peaks");
  });

  it("builds section hrefs", () => {
    expect(energySectionHref("akarp", "flow")).toBe("/sites/akarp/energy");
    expect(energySectionHref("akarp", "history")).toBe("/sites/akarp/energy#historik");
  });
});

describe("energyDashboardHelpers", () => {
  const readings = [
    {
      recorded_at: "2026-08-27T10:00:00Z",
      solar_production_w: 1000,
      consumption_w: 2000,
      grid_import_w: 500,
      grid_export_w: 0,
      battery_soc_pct: 50,
      battery_power_w: 300,
    },
    {
      recorded_at: "2026-08-27T10:15:00Z",
      solar_production_w: 1500,
      consumption_w: 1800,
      grid_import_w: 0,
      grid_export_w: 200,
      battery_soc_pct: 55,
      battery_power_w: 400,
    },
    {
      recorded_at: "2026-08-27T10:30:00Z",
      solar_production_w: 1200,
      consumption_w: 1600,
      grid_import_w: 0,
      grid_export_w: 100,
      battery_soc_pct: 52,
      battery_power_w: -400,
    },
  ];

  it("integrates battery charge and discharge from readings", () => {
    const result = integrateBatteryKwh(readings);
    expect(result.chargeKwh).toBeGreaterThan(0);
    expect(result.dischargeKwh).toBeGreaterThan(0);
  });

  it("builds live metrics from dashboard live section", () => {
    const live = buildLiveMetrics({
      solar_production_w: 540,
      consumption_w: 1780,
      grid_import_w: 0,
      grid_export_w: 1240,
      battery_soc_pct: 58,
      battery_power_w: -460,
      battery_direction: "charging",
      ev_power_w: 0,
      status: "ok",
      stale: false,
    });
    expect(live.solarW).toBe(540);
    expect(live.gridNetW).toBe(1240);
    expect(live.batteryDirection).toBe("charging");
  });

  it("builds today metrics and balance slices", () => {
    const today = buildTodayMetrics(
      {
        produced_kwh: 8.8,
        consumed_kwh: 9.7,
        imported_kwh: 0,
        exported_kwh: 8.1,
        energy_cost_sek: 0,
        savings_sek: 0,
        status: "ok",
        stale: false,
      },
      { chargeKwh: 4.7, dischargeKwh: 2.1 },
    );
    const balance = buildEnergyBalance(today);
    expect(balance.slices).toHaveLength(3);
    expect(balance.centerLabel).toBe("Överskott");
    expect(today.batteryChargeKwh).toBe(4.7);
  });

  it("builds chart series in kW", () => {
    const series = buildFlowChartSeries(readings);
    expect(series).toHaveLength(3);
    expect(series[0].solarKw).toBe(1);
    expect(series[2].batteryDischargeKw).toBeCloseTo(0.4, 1);
  });

  it("summarizes peak readings including consumption", () => {
    const summary = peakSummary([
      {
        period_start: "2026-08-27",
        solar_production_w: 8800,
        consumption_w: 9700,
        battery_charge_w: 9400,
        battery_discharge_w: 9700,
      },
    ]);
    expect(summary.consumption).toBe(9700);
  });
});
