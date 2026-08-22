import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import VirtualEvseDiagnosticsPanel from "./VirtualEvseDiagnosticsPanel";

const mockFetchEnergyBalance = vi.fn();
const mockFetchVirtualEvseStatus = vi.fn();
const mockFetchSiteEnergyConfig = vi.fn();
const mockUpdateEvCharger = vi.fn();
const mockUpdateSiteEnergyConfig = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchEnergyBalance: (...args: unknown[]) => mockFetchEnergyBalance(...args),
    fetchVirtualEvseStatus: (...args: unknown[]) => mockFetchVirtualEvseStatus(...args),
    fetchSiteEnergyConfig: (...args: unknown[]) => mockFetchSiteEnergyConfig(...args),
    updateEvCharger: (...args: unknown[]) => mockUpdateEvCharger(...args),
    updateSiteEnergyConfig: (...args: unknown[]) => mockUpdateSiteEnergyConfig(...args),
  };
});

describe("VirtualEvseDiagnosticsPanel", () => {
  beforeEach(() => {
    mockFetchSiteEnergyConfig.mockResolvedValue({
      site_slug: "akarp",
      load_includes_ev_charger: null,
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      physical_ev_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });
    mockUpdateEvCharger.mockResolvedValue({});
    mockUpdateSiteEnergyConfig.mockResolvedValue({
      site_slug: "akarp",
      load_includes_ev_charger: true,
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      physical_ev_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });
  });

  it("renders physical system, EV, SEMP and flow diagnostics", async () => {
    mockFetchEnergyBalance.mockResolvedValue({
      charger_id: 1,
      recorded_at: "2026-08-21T10:00:00Z",
      status: "OK",
      flags: [],
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      sungrow_pv_power_w: 5000,
      sungrow_load_power_w: 12000,
      sungrow_grid_import_w: 1000,
      sungrow_grid_export_w: 0,
      sungrow_battery_charge_w: 0,
      sungrow_battery_discharge_w: 0,
      sungrow_battery_soc_pct: 55,
      sungrow_fresh: true,
      sungrow_telemetry_age_seconds: 5,
      halo_power_w: 10000,
      virtual_evse_reported_power_w: 10000,
      heartbeat_observed_ev_power_w: 9800,
      heartbeat_home_consumption_w: 12000,
      non_ev_house_load_w: 2000,
      non_ev_house_load_reason: null,
      residual_w: 100,
      alignment_delta_seconds: 1,
      energy_flow_line: "PV 5.0kW → Load 12.0kW | EV 10.0kW",
    });

    mockFetchVirtualEvseStatus.mockResolvedValue({
      charger_id: 1,
      virtual_evse_enabled: true,
      semp_device_id: "emic-evse-1",
      status: "Charging",
      reported_power_w: 10000,
      halo_power_w: 10000,
      heartbeat_observed_ev_power_w: 9800,
      heartbeat_detected: true,
      vehicle_connected: true,
      stale: false,
      physical_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });

    render(
      <VirtualEvseDiagnosticsPanel siteSlug="akarp" chargerId={1} refreshSeconds={30} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("virtual-evse-diagnostics")).toBeInTheDocument();
    });

    expect(screen.getByText(/Sungrow Hybrid Inverter SH10/)).toBeInTheDocument();
    expect(screen.getByText(/Heartbeat detected: YES/)).toBeInTheDocument();
    expect(screen.getByText(/PV 5.0kW → Load 12.0kW \| EV 10.0kW/)).toBeInTheDocument();
  });

  it("shows heartbeat detected when idle EV power is zero", async () => {
    mockFetchEnergyBalance.mockResolvedValue({
      charger_id: 1,
      recorded_at: "2026-08-21T10:00:00Z",
      status: "OK",
      flags: [],
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      sungrow_pv_power_w: 5000,
      sungrow_load_power_w: 3000,
      sungrow_grid_import_w: 0,
      sungrow_grid_export_w: 2000,
      sungrow_battery_charge_w: 0,
      sungrow_battery_discharge_w: 0,
      sungrow_battery_soc_pct: 55,
      sungrow_fresh: true,
      sungrow_telemetry_age_seconds: 5,
      halo_power_w: 0,
      virtual_evse_reported_power_w: 0,
      heartbeat_observed_ev_power_w: 0,
      heartbeat_home_consumption_w: 3000,
      non_ev_house_load_w: 3000,
      non_ev_house_load_reason: null,
      residual_w: 0,
      alignment_delta_seconds: 1,
      energy_flow_line: "PV 5.0kW → Load 3.0kW",
    });

    mockFetchVirtualEvseStatus.mockResolvedValue({
      charger_id: 1,
      virtual_evse_enabled: true,
      semp_device_id: "emic-evse-1",
      status: "Idle",
      reported_power_w: 0,
      halo_power_w: 0,
      heartbeat_observed_ev_power_w: 0,
      heartbeat_detected: true,
      vehicle_connected: false,
      stale: false,
      physical_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });

    render(
      <VirtualEvseDiagnosticsPanel siteSlug="akarp" chargerId={1} refreshSeconds={30} />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Heartbeat detected: YES/)).toBeInTheDocument();
    });
  });

  it("shows degraded badge when balance status is degraded", async () => {
    mockFetchEnergyBalance.mockResolvedValue({
      charger_id: 1,
      recorded_at: null,
      status: "DEGRADED",
      flags: ["sungrow_stale"],
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      sungrow_pv_power_w: null,
      sungrow_load_power_w: null,
      sungrow_grid_import_w: null,
      sungrow_grid_export_w: null,
      sungrow_battery_charge_w: null,
      sungrow_battery_discharge_w: null,
      sungrow_battery_soc_pct: null,
      sungrow_fresh: false,
      sungrow_telemetry_age_seconds: 120,
      halo_power_w: 5000,
      virtual_evse_reported_power_w: 5000,
      heartbeat_observed_ev_power_w: null,
      heartbeat_home_consumption_w: null,
      non_ev_house_load_w: null,
      non_ev_house_load_reason: "sungrow_stale",
      residual_w: null,
      alignment_delta_seconds: null,
      energy_flow_line: null,
    });

    mockFetchVirtualEvseStatus.mockResolvedValue({
      charger_id: 1,
      virtual_evse_enabled: true,
      semp_device_id: "emic-evse-1",
      status: "Charging",
      reported_power_w: 5000,
      halo_power_w: 5000,
      heartbeat_observed_ev_power_w: null,
      heartbeat_detected: false,
      vehicle_connected: true,
      stale: false,
      physical_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });

    render(
      <VirtualEvseDiagnosticsPanel siteSlug="akarp" chargerId={1} refreshSeconds={30} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("balance-status-badge")).toHaveTextContent("DEGRADED");
    });
  });

  it("saves virtual evse and load-includes settings", async () => {
    mockFetchEnergyBalance.mockResolvedValue({
      charger_id: 1,
      recorded_at: "2026-08-21T10:00:00Z",
      status: "OK",
      flags: [],
      inverter_display_name: "Sungrow Hybrid Inverter SH10",
      sungrow_pv_power_w: 5000,
      sungrow_load_power_w: 12000,
      sungrow_grid_import_w: 1000,
      sungrow_grid_export_w: 0,
      sungrow_battery_charge_w: 0,
      sungrow_battery_discharge_w: 0,
      sungrow_battery_soc_pct: 55,
      sungrow_fresh: true,
      sungrow_telemetry_age_seconds: 5,
      halo_power_w: 10000,
      virtual_evse_reported_power_w: 10000,
      heartbeat_observed_ev_power_w: 9800,
      heartbeat_home_consumption_w: 12000,
      non_ev_house_load_w: 2000,
      non_ev_house_load_reason: null,
      residual_w: 100,
      alignment_delta_seconds: 1,
      energy_flow_line: "PV 5.0kW → Load 12.0kW | EV 10.0kW",
    });
    mockFetchVirtualEvseStatus.mockResolvedValue({
      charger_id: 1,
      virtual_evse_enabled: false,
      semp_device_id: null,
      status: "Idle",
      reported_power_w: 0,
      halo_power_w: 0,
      heartbeat_observed_ev_power_w: null,
      heartbeat_detected: false,
      vehicle_connected: false,
      stale: false,
      physical_charger_label: "Charge Amps Halo",
      ev_vehicle_label: "Mercedes EQE 500",
    });

    render(
      <VirtualEvseDiagnosticsPanel siteSlug="akarp" chargerId={1} refreshSeconds={30} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("virtual-evse-settings")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByText("Virtual EVSE aktiv").parentElement!.querySelector("select")!, {
      target: { value: "true" },
    });
    fireEvent.change(
      screen.getByText("HB huslast inkluderar EV-laddare").parentElement!.querySelector("select")!,
      { target: { value: "true" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Spara diagnostikinställningar" }));

    await waitFor(() => {
      expect(mockUpdateEvCharger).toHaveBeenCalledWith("akarp", 1, { virtual_evse_enabled: true });
      expect(mockUpdateSiteEnergyConfig).toHaveBeenCalledWith("akarp", {
        load_includes_ev_charger: true,
      });
    });
  });
});
