import { describe, expect, it } from "vitest";
import {
  averageChargingPowerKw,
  computeCo2SavedKg,
  sessionAveragePowerW,
  formatEvDuration,
  modeLabel,
  sessionSourceLabel,
  totalChargeMinutesToday,
  buildPowerChartFromHistory,
} from "./evDashboardHelpers";
import type { EvChargingSession } from "@/lib/api";
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
    const label = sessionSourceLabel(
      sessionWithSources({ solar_direct_kwh: 10, solar_battery_kwh: 0, grid_battery_kwh: 0, grid_direct_kwh: 0 }),
    );
    expect(label.label).toBe("Sol");
  });
});

function sessionWithSources(
  energy_sources: EvChargingSession["energy_sources"],
  average_cost_sek_per_kwh: number | null = 0,
): EvChargingSession {
  const total =
    energy_sources.solar_direct_kwh +
    energy_sources.solar_battery_kwh +
    energy_sources.grid_battery_kwh +
    energy_sources.grid_direct_kwh;
  return {
    id: 1,
    charger_id: 1,
    started_at: "2026-08-24T08:00:00Z",
    ended_at: "2026-08-24T10:00:00Z",
    status: "completed",
    total_energy_kwh: total,
    energy_sources,
    actual_cost_sek: 0,
    reference_cost_sek: 0,
    savings_sek: 0,
    smart_charging_savings_sek: 0,
    solar_contribution_sek: 0,
    renewable_share_pct: 0,
    grid_share_pct: 0,
    average_cost_sek_per_kwh,
    energy_quality: "good",
    cost_quality: "good",
    attribution_quality: "good",
    savings_baseline: "immediate",
    calculation_version: "1",
    reconciliation_delta_kwh: 0,
    intervals: [],
  } as EvChargingSession;
}

describe("sessionAveragePowerW", () => {
  const session = (over: Record<string, unknown>) =>
    ({
      id: 1,
      started_at: "2026-08-22T09:21:00Z",
      ended_at: "2026-08-22T10:21:00Z",
      total_energy_kwh: 2.0,
      energy_sources: {
        solar_direct_kwh: 0,
        solar_battery_kwh: 0,
        grid_battery_kwh: 0,
        grid_direct_kwh: 2.0,
      },
      ...over,
    }) as never;

  it("reports watts, not a thousandth of them", () => {
    expect(sessionAveragePowerW(session({}))).toBeCloseTo(2000, 0);
  });

  it("spreads a long slow session over its whole duration", () => {
    const w = sessionAveragePowerW(
      session({ ended_at: "2026-08-23T06:21:00Z", total_energy_kwh: 2.44 }),
    );
    expect(w).toBeCloseTo(2440 / 21, 0);
  });

  it("measures an ongoing session up to now", () => {
    const w = sessionAveragePowerW(
      session({ started_at: new Date(Date.now() - 3_600_000).toISOString(), ended_at: null }),
    );
    expect(w).toBeCloseTo(2000, -2);
  });

  it("has nothing to report without energy", () => {
    expect(sessionAveragePowerW(session({ total_energy_kwh: 0 }))).toBeNull();
    expect(sessionAveragePowerW(session({ total_energy_kwh: null }))).toBeNull();
  });

  it("refuses to divide by a non-positive duration", () => {
    expect(sessionAveragePowerW(session({ ended_at: "2026-08-22T09:21:00Z" }))).toBeNull();
  });
});

describe("averageChargingPowerKw", () => {
  const snapshot = (halo_power_w: number) => ({
    charger_id: 1,
    recorded_at: "2026-08-30T12:00:00Z",
    halo_power_w,
    virtual_evse_reported_power_w: halo_power_w,
  });

  it("averages the samples where the car is actually drawing", () => {
    const kw = averageChargingPowerKw([snapshot(11000), snapshot(13000)] as never);
    expect(kw).toBeCloseTo(12, 3);
  });

  it("ignores idle samples instead of letting them drag the mean down", () => {
    const kw = averageChargingPowerKw([snapshot(12000), snapshot(0), snapshot(10)] as never);
    expect(kw).toBeCloseTo(12, 3);
  });

  it("reports zero when nothing has been charging", () => {
    expect(averageChargingPowerKw([snapshot(0)] as never)).toBe(0);
    expect(averageChargingPowerKw([] as never)).toBe(0);
  });

  it("falls back to the virtual meter when the halo reading is missing", () => {
    const kw = averageChargingPowerKw([
      { charger_id: 1, recorded_at: "2026-08-30T12:00:00Z", virtual_evse_reported_power_w: 7000 },
    ] as never);
    expect(kw).toBeCloseTo(7, 3);
  });
});

describe("totalChargeMinutesToday", () => {
  it("returns whole minutes so the panel does not print a raw float", () => {
    const today = new Date().toISOString().slice(0, 10);
    const session = sessionWithSources({
      solar_direct_kwh: 1,
      solar_battery_kwh: 0,
      grid_battery_kwh: 0,
      grid_direct_kwh: 0,
    });
    const minutes = totalChargeMinutesToday([
      { ...session, started_at: `${today}T08:00:00Z`, ended_at: `${today}T09:35:40Z` },
    ]);
    expect(minutes).toBe(96);
  });

  it("ignores sessions from other days", () => {
    const session = sessionWithSources({
      solar_direct_kwh: 1,
      solar_battery_kwh: 0,
      grid_battery_kwh: 0,
      grid_direct_kwh: 0,
    });
    expect(
      totalChargeMinutesToday([
        { ...session, started_at: "2020-01-01T08:00:00Z", ended_at: "2020-01-01T09:00:00Z" },
      ]),
    ).toBe(0);
  });
});

describe("sessionSourceLabel", () => {
  it("says it does not know rather than guessing grid when there is no split", () => {
    const label = sessionSourceLabel(
      sessionWithSources({
        solar_direct_kwh: 0,
        solar_battery_kwh: 0,
        grid_battery_kwh: 0,
        grid_direct_kwh: 0,
      }),
    );
    expect(label.label).toBe("Okänd");
    expect(label.tone).toBe("unknown");
    expect(label.detail).toMatch(/Ingen källfördelning/);
  });

  it("says an unfinished session is still running", () => {
    const session = sessionWithSources({
      solar_direct_kwh: 0,
      solar_battery_kwh: 0,
      grid_battery_kwh: 0,
      grid_direct_kwh: 0,
    });
    const label = sessionSourceLabel({ ...session, ended_at: null });
    expect(label.label).toBe("Pågår");
    expect(label.detail).toMatch(/avslutas/);
  });

  it("calls a session grid when a trace of sun does not change the story", () => {
    // The real 22 Aug session: 75.66 kWh of which 0.08 solar and 0.05 via battery.
    const label = sessionSourceLabel(
      sessionWithSources(
        { solar_direct_kwh: 0.08, solar_battery_kwh: 0, grid_battery_kwh: 0.05, grid_direct_kwh: 75.54 },
        2.0,
      ),
    );
    expect(label.label).toBe("Nät (dyrt)");
    expect(label.tone).toBe("grid");
    // A fraction of a percent must not be dressed up as a round zero.
    expect(label.detail).toBe("Sol 0.08 kWh (<1 %) · Batteri 0.05 kWh (<1 %) · Nät 75.5 kWh (100 %)");
  });

  it("names both sources with the dominant share when the mix is real", () => {
    // The real 21 Aug 12:17 session: 1.86 kWh of which 1.24 straight from the roof.
    const label = sessionSourceLabel(
      sessionWithSources(
        { solar_direct_kwh: 1.24, solar_battery_kwh: 0, grid_battery_kwh: 0, grid_direct_kwh: 0.63 },
        0.9,
      ),
    );
    expect(label.label).toBe("Sol 66 % + Nät");
    expect(label.tone).toBe("mixed");
    expect(label.detail).toBe("Sol 1.2 kWh (66 %) · Nät 0.63 kWh (34 %)");
  });

  it("credits the battery as its own path", () => {
    const label = sessionSourceLabel(
      sessionWithSources({
        solar_direct_kwh: 0,
        solar_battery_kwh: 6,
        grid_battery_kwh: 4,
        grid_direct_kwh: 0,
      }),
    );
    expect(label.label).toBe("Batteri");
    expect(label.tone).toBe("battery");
  });

  it("marks cheap grid charging separately from expensive", () => {
    const sources = {
      solar_direct_kwh: 0,
      solar_battery_kwh: 0,
      grid_battery_kwh: 0,
      grid_direct_kwh: 20,
    };
    expect(sessionSourceLabel(sessionWithSources(sources, 0.8)).label).toBe("Nät (lågpris)");
    expect(sessionSourceLabel(sessionWithSources(sources, 2.4)).label).toBe("Nät (dyrt)");
    expect(sessionSourceLabel(sessionWithSources(sources, null)).label).toBe("Nät");
  });

  it("reports the split even for a three-way mix", () => {
    const label = sessionSourceLabel(
      sessionWithSources({
        solar_direct_kwh: 5,
        solar_battery_kwh: 3,
        grid_battery_kwh: 0,
        grid_direct_kwh: 2,
      }),
    );
    expect(label.label).toBe("Sol 50 % + Batteri");
    expect(label.detail).toBe("Sol 5.0 kWh (50 %) · Batteri 3.0 kWh (30 %) · Nät 2.0 kWh (20 %)");
  });
});
