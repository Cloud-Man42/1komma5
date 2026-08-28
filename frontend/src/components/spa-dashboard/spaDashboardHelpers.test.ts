import { describe, expect, it } from "vitest";
import {
  buildComponentRows,
  buildInsights,
  buildSensorRows,
  filterSchedulePanelCopy,
  fixedScheduleWarningSv,
  filterProgressPct,
  integrationLabelSv,
  isFilterRunning,
  isFixedScheduleIncomplete,
  isUvActive,
  recommendedFixedScheduleTimes,
  sensorStatusLabel,
  strategyHintSv,
  shadowModeHintSv,
  strategyLabelSv,
  tempStable,
} from "./spaDashboardHelpers";
import type { SpaControlConfig, SpaEnergyPeriod, SpaPlan, SpaStatus } from "@/lib/api";

function status(partial: Partial<SpaStatus> = {}): SpaStatus {
  return {
    consumer_id: 1,
    site_slug: "akarp",
    online: true,
    water_temperature_c: 37.8,
    set_temperature_c: 38,
    heater_active: true,
    pump_label: "Pump 1: High",
    filter_status: "Filtering",
    errors: [],
    current_power_w: 2450,
    power_breakdown: { heater: 2000, pump1: 2100, pump2: 250, circulation: 100 },
    power_note_sv: "",
    last_updated: "2026-08-27T08:00:00Z",
    data_source: "ARCTIC_SPA_REST",
    data_quality: "CALCULATED",
    integration_enabled: true,
    ...partial,
  };
}

describe("spaDashboardHelpers", () => {
  it("maps strategy labels", () => {
    expect(strategyLabelSv("eco_smart")).toBe("Eco");
    expect(strategyLabelSv("fixed")).toBe("Fast");
  });

  it("maps Arctic integration label to Eco Pak", () => {
    expect(integrationLabelSv("ARCTIC_SPA_REST")).toBe("Eco Pak");
    expect(integrationLabelSv("OTHER")).toBe("OTHER");
  });

  it("builds component rows from breakdown", () => {
    const rows = buildComponentRows(status());
    expect(rows.find((r) => r.id === "heater")?.powerW).toBe(2000);
    expect(rows.find((r) => r.id === "pump-1")?.status).toBe("Hög");
  });

  it("detects stable temperature", () => {
    expect(tempStable(status())).toBe(true);
    expect(tempStable(status({ water_temperature_c: 35 }))).toBe(false);
  });

  it("detects active filter cycle only with measurable load", () => {
    expect(
      isFilterRunning({
        ...status(),
        filter_status: "Filtering",
        filter_cycle_active: false,
        current_power_w: 0,
        power_breakdown: {},
      }),
    ).toBe(false);
    expect(
      isFilterRunning({
        ...status(),
        filter_status: "Filtering",
        filter_cycle_active: true,
        current_power_w: 2100,
      }),
    ).toBe(true);
  });

  it("uses backend filter_cycle_active when provided", () => {
    expect(
      isFilterRunning({
        ...status(),
        filter_status: "Filtering",
        filter_cycle_active: false,
      }),
    ).toBe(false);
  });

  it("builds sensor rows from status and health", () => {
    const rows = buildSensorRows(status(), {
      consumer_id: 1,
      api_status: "OK",
      spa_status: "ONLINE",
      polling_status: "ACTIVE",
      database_status: "OK",
      last_success_at: null,
      last_sample_at: null,
      samples_last_24h: 12,
      samples_with_power_24h: 10,
      sample_energy_kwh_24h: 1.8,
      intervals_last_24h: 11,
      data_quality: "MEASURED",
      measured_pct: 80,
      calculated_pct: 20,
      estimated_pct: 0,
      missing_pct: 0,
      last_error: null,
      actuator_state: "IDLE",
      integration_degraded: false,
      integration_degraded_message_sv: "",
    });
    expect(rows.find((row) => row.label === "Vattentemperatur")?.value).toContain("°C");
    expect(rows.some((row) => row.label === "API-status" && row.value === "OK")).toBe(true);
  });

  it("detects UV during filter circulation", () => {
    expect(
      isUvActive({
        ...status(),
        filter_status: "Idle",
        filter_cycle_active: false,
        current_power_w: 150,
        power_breakdown: { pump1: 150 },
      }),
    ).toBe(false);
    expect(
      isUvActive({
        ...status(),
        filter_status: "Filtering",
        filter_cycle_active: true,
        current_power_w: 200,
        power_breakdown: { circulation: 200 },
      }),
    ).toBe(true);
    expect(
      isUvActive({
        ...status(),
        filter_status: "Sanitize",
        filter_cycle_active: false,
        current_power_w: 150,
        power_breakdown: { pump1: 150 },
      }),
    ).toBe(true);
  });

  it("labels unknown sensors", () => {
    expect(sensorStatusLabel(null)).toBe("Ej rapporterad");
    expect(sensorStatusLabel(true)).toBe("På");
    expect(sensorStatusLabel(false)).toBe("Av");
  });

  it("builds insights from today solar share", () => {
    const today = { own_energy_pct: 62, max_power_w: 5600, actual_cost_sek: 4.32 } as SpaEnergyPeriod;
    const month = { actual_cost_sek: 57.86 } as SpaEnergyPeriod;
    const insights = buildInsights(today, month, null, status());
    expect(insights[0]?.text).toContain("62%");
  });

  it("detects incomplete fixed schedule", () => {
    const base = {
      strategy: "FIXED_SCHEDULE",
      fixed_schedule_start: null,
      fixed_schedule_end: null,
      filter_optimization_enabled: true,
      shadow_mode: true,
    } as SpaControlConfig;
    expect(isFixedScheduleIncomplete(base)).toBe(true);
    expect(fixedScheduleWarningSv(base)).toContain("Shadow mode");
    expect(recommendedFixedScheduleTimes({ allowed_window_start: "07:00", allowed_window_end: "22:00" })).toEqual({
      start: "07:00",
      end: "22:00",
    });
  });

  it("builds fixed schedule panel copy", () => {
    const copy = filterSchedulePanelCopy({
      strategy: "FIXED_SCHEDULE",
      fixed_schedule_start: null,
      fixed_schedule_end: null,
      allowed_window_start: "07:00",
      allowed_window_end: "22:00",
      filter_cycles_per_day: 4,
      filter_duration_minutes: 120,
      filter_optimization_enabled: true,
      shadow_mode: true,
    } as SpaControlConfig);
    expect(copy.subtitle).toContain("ofullständigt");
    expect(copy.warning).toContain("Fast schema saknar");
    expect(copy.checklist.some((item) => item.includes("Shadow mode"))).toBe(true);
  });

  it("describes strategy hints", () => {
    expect(strategyHintSv("FIXED_SCHEDULE")).toContain("Eco Pak");
  });

  it("describes shadow mode hints", () => {
    expect(shadowModeHintSv(true)).toContain("automatiska");
    expect(shadowModeHintSv(false)).toContain("automatiska");
  });
});
