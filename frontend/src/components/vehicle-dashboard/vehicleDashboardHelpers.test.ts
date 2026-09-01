import { describe, expect, it } from "vitest";
import {
  buildVehicleDisplay,
  chargingSubtitle,
  estimateCo2SavedKg,
  recentSessionEnergyBars,
  resolveTargetSocPct,
  sessionEnergyKwh,
  surplusLabel,
} from "./vehicleDashboardHelpers";
import type {
  EnergyReasoning,
  VehicleChargeSession,
  VehicleIntegrationStatus,
  VehicleListItem,
} from "@/lib/api";

const vehicle: VehicleListItem = {
  id: 1,
  site_id: 1,
  provider: "MERCEDES_ME",
  display_name: "Mercedes EQE 500 Sedan",
  manufacturer: "Mercedes-Benz",
  model: "EQE 500",
  masked_vin: "W1***",
  enabled: true,
  connection_state: "CONNECTED",
  data_quality: "LIVE",
  freshness_label: "LIVE",
  state_of_charge_percent: 78,
  target_soc_percent: 80,
  electric_range_km: 412,
  is_plugged_in: true,
  is_charging: true,
  charging_power_kw: 6.8,
  last_vehicle_update: "2026-08-27T17:00:00Z",
  capabilities: {
    can_read_soc: true,
    can_read_range: true,
    can_read_charging_state: true,
    can_read_charging_power: true,
    can_read_target_soc: true,
    can_read_departure_time: true,
    can_set_target_soc: true,
    can_start_charging: true,
    can_stop_charging: true,
  },
  halo_correlation: null,
};

const session: VehicleChargeSession = {
  id: 10,
  vehicle_id: 1,
  charger_id: 1,
  connected_at: "2026-08-27T12:22:00Z",
  disconnected_at: null,
  charging_started_at: "2026-08-27T12:22:00Z",
  charging_stopped_at: null,
  start_soc: 55,
  end_soc: null,
  target_soc: 80,
  status: "ACTIVE",
  halo_energy_kwh: 28.7,
  estimated_battery_energy_delta_kwh: 28.7,
  energy_sources: {
    solar_direct_kwh: 28.7,
    solar_battery_kwh: 0,
    grid_battery_kwh: 0,
    grid_direct_kwh: 0,
  },
  actual_cost_sek: 0,
  reference_cost_sek: 12,
  savings_sek: 12,
  renewable_share_pct: 100,
  grid_share_pct: 0,
  identification_confidence: 0.95,
  energy_quality: "MEASURED",
  cost_quality: "CALCULATED",
  attribution_quality: "HIGH",
};

const integration: VehicleIntegrationStatus = {
  site_slug: "akarp",
  provider: "MERCEDES_ME",
  enabled: true,
  region: "ECE",
  username: "user@test.com",
  password_configured: true,
  connection_state: "CONNECTED",
  commands_enabled: true,
  token_expires_at: null,
  last_error: null,
  last_error_at: null,
  backoff_until: null,
  blocked_since: null,
  reconnect_count: 0,
  http_429_count: 0,
  decode_failure_count: 0,
  health: "HEALTHY",
};

describe("vehicleDashboardHelpers", () => {
  it("builds display from live vehicle and session", () => {
    const display = buildVehicleDisplay({
      vehicle,
      session,
      sessions: [session],
      integration,
      reasoning: null,
      refreshIntervalSec: 15,
      siteSlug: "akarp",
    });

    expect(display.socPct).toBe(78);
    expect(display.chargedTodayKwh).toBe(28.7);
    expect(display.canStopCharging).toBe(true);
    expect(display.surplusLabel).toBe("100% förnybar");
  });

  it("computes session energy and bars", () => {
    expect(sessionEnergyKwh(session)).toBe(28.7);
    expect(recentSessionEnergyBars([session])).toEqual([100]);
    expect(estimateCo2SavedKg(28.7)).toBeCloseTo(4.305);
    expect(surplusLabel(session)).toBe("100% förnybar");
  });
});

describe("resolveTargetSocPct", () => {
  const withoutTargetSoc: VehicleListItem = {
    ...vehicle,
    target_soc_percent: 0,
    capabilities: { ...vehicle.capabilities, can_read_target_soc: false },
  };

  it("uses the target the car reports", () => {
    expect(resolveTargetSocPct(vehicle, null, null)).toBe(80);
  });

  it("ignores the car's 0% when it cannot read a charge limit", () => {
    expect(resolveTargetSocPct(withoutTargetSoc, null, null)).toBeNull();
  });

  it("falls back to the session target when the car reports nothing", () => {
    expect(resolveTargetSocPct(withoutTargetSoc, session, null)).toBe(80);
  });

  it("falls back to the charging plan when neither car nor session has a target", () => {
    const plan = { vehicle_target_soc_pct: 65 } as EnergyReasoning;
    expect(resolveTargetSocPct(withoutTargetSoc, { ...session, target_soc: null }, plan)).toBe(65);
  });

  it("treats a 0% target from any source as no target at all", () => {
    const plan = { vehicle_target_soc_pct: 0 } as EnergyReasoning;
    expect(resolveTargetSocPct(withoutTargetSoc, { ...session, target_soc: 0 }, plan)).toBeNull();
  });

  it("reports no target when there is no vehicle", () => {
    expect(resolveTargetSocPct(null, null, null)).toBeNull();
  });

  it("keeps a 0% reading out of the built display", () => {
    const display = buildVehicleDisplay({
      vehicle: withoutTargetSoc,
      session: { ...session, target_soc: null },
      sessions: [],
      integration,
      reasoning: null,
      refreshIntervalSec: 15,
      siteSlug: "akarp",
    });

    expect(display.targetSocPct).toBeNull();
  });

  it("does not claim the car is plugged in when Mercedes data is stale", () => {
    expect(
      chargingSubtitle(
        { ...vehicle, freshness_label: "INAKTUELL", is_plugged_in: null, is_charging: null },
        session,
        null,
      ),
    ).toContain("Ingen färsk fordonsdata");
  });

  it("uses value envelopes when top-level charging fields are nulled for stale guard", () => {
    const display = buildVehicleDisplay({
      vehicle: {
        ...vehicle,
        freshness_label: "INAKTUELL",
        is_charging: null,
        charging_power_kw: null,
        charging_power: {
          value: 10.9,
          source_timestamp: "2026-08-31T18:57:43.397287Z",
          received_timestamp: "2026-08-31T18:57:43.397287Z",
          age_seconds: 120,
          quality: "RECENT",
        },
      },
      session: null,
      sessions: [],
      integration,
      reasoning: null,
      refreshIntervalSec: 15,
      siteSlug: "akarp",
    });

    expect(display.chargingPowerKw).toBe(10.9);
    expect(display.isCharging).toBe(true);
  });

  it("ignores orphaned active sessions when the car is unplugged", () => {
    const display = buildVehicleDisplay({
      vehicle: { ...vehicle, is_plugged_in: false, is_charging: false, charging_power_kw: 0 },
      session,
      sessions: [session],
      integration,
      reasoning: null,
      refreshIntervalSec: 15,
      siteSlug: "akarp",
    });

    expect(display.activeSession).toBeNull();
    expect(display.chargedTodayKwh).toBe(0);
    expect(display.isCharging).toBe(false);
  });
});
