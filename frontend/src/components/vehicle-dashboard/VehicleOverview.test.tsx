import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VehicleOverview } from "./VehicleOverview";

const mockFetchVehicles = vi.fn();
const mockFetchVehicleIntegrationStatus = vi.fn();
const mockFetchVehicleChargeSessions = vi.fn();
const mockFetchCurrentVehicleChargeSession = vi.fn();
const mockFetchEnergyReasoning = vi.fn();
const mockStopVehicleCharging = vi.fn();
const mockStartVehicleCharging = vi.fn();
const mockSyncVehicles = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchVehicles: (...args: unknown[]) => mockFetchVehicles(...args),
    fetchVehicleIntegrationStatus: (...args: unknown[]) => mockFetchVehicleIntegrationStatus(...args),
    fetchVehicleChargeSessions: (...args: unknown[]) => mockFetchVehicleChargeSessions(...args),
    fetchCurrentVehicleChargeSession: (...args: unknown[]) => mockFetchCurrentVehicleChargeSession(...args),
    fetchEnergyReasoning: (...args: unknown[]) => mockFetchEnergyReasoning(...args),
    stopVehicleCharging: (...args: unknown[]) => mockStopVehicleCharging(...args),
    startVehicleCharging: (...args: unknown[]) => mockStartVehicleCharging(...args),
    syncVehicles: (...args: unknown[]) => mockSyncVehicles(...args),
  };
});

const vehicle = {
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
  halo_correlation: {
    charger_id: 2,
    confidence: 0.9,
    status: "MATCH",
    plugged_agreement: true,
    charging_agreement: true,
    power_delta_kw: 0.1,
    vehicle_power_kw: 6.8,
    halo_power_kw: 6.7,
    notes: "OK",
    updated_at: "2026-08-27T17:00:00Z",
  },
};

const session = {
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

const integration = {
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

function setHash(hash: string) {
  window.location.hash = hash;
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

describe("VehicleOverview sections", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.location.hash = "";
    mockFetchVehicles.mockResolvedValue({ site_slug: "akarp", vehicles: [vehicle] });
    mockFetchVehicleIntegrationStatus.mockResolvedValue(integration);
    mockFetchVehicleChargeSessions.mockResolvedValue({ site_slug: "akarp", vehicle_id: 1, sessions: [session] });
    mockFetchCurrentVehicleChargeSession.mockResolvedValue(session);
    mockFetchEnergyReasoning.mockResolvedValue({
      charger_id: 2,
      vehicle_target_soc_pct: 80,
      vehicle_departure_time: "2026-08-28T07:00:00Z",
      vehicle_required_energy_kwh: 12,
      decision_reason_sv: "Laddar med överskott från solen",
      smart_charging_state: "SOLAR_FIRST",
    });
    mockStopVehicleCharging.mockResolvedValue({ success: true, vehicle_id: 1, message: "Laddning stoppad", command: "stop" });
    mockStartVehicleCharging.mockResolvedValue({ success: true, vehicle_id: 1, message: "Laddning startad", command: "start" });
    mockSyncVehicles.mockResolvedValue({
      site_slug: "akarp",
      synced_at: "2026-08-31T10:00:00Z",
      vehicles_updated: 1,
      vehicles: [vehicle],
    });
  });

  it("renders overview section by default", async () => {
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByText("Översikt")).toBeInTheDocument();
    });

    expect(screen.getByTestId("vehicle-battery-card")).toHaveTextContent("78%");
    expect(screen.getByTestId("vehicle-summary-strip")).toHaveTextContent("W1***");
    expect(screen.queryByTestId("vehicle-section-charging")).not.toBeInTheDocument();
  });

  it("renders charging section with session controls", async () => {
    setHash("#laddning");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-charging")).toBeInTheDocument();
    });

    expect(screen.getByText("Laddning")).toBeInTheDocument();
    expect(screen.getByTestId("vehicle-charging-session")).toHaveTextContent("28.7 kWh");
    expect(screen.getByTestId("vehicle-actions")).toHaveTextContent("Sätt mål-SoC");
  });

  it("renders history section with session list", async () => {
    setHash("#resor");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-history")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Laddhistorik" })).toBeInTheDocument();
    expect(screen.getByText("1 sessioner")).toBeInTheDocument();
  });

  it("renders status section with halo correlation", async () => {
    setHash("#status");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-status")).toBeInTheDocument();
    });

    expect(screen.getByTestId("vehicle-halo-status")).toHaveTextContent("MATCH");
  });

  it("renders costs section", async () => {
    setHash("#kostnad");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-costs")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Kostnad & analys" })).toBeInTheDocument();
    expect(screen.getByText("Total besparing")).toBeInTheDocument();
  });

  it("renders schedule section", async () => {
    setHash("#schema");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-schedule")).toBeInTheDocument();
    });

    expect(screen.getByTestId("vehicle-charging-plan")).toBeInTheDocument();
  });

  it("renders settings section", async () => {
    setHash("#installningar");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-section-settings")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Inställningar" })).toBeInTheDocument();
    expect(screen.getByTestId("mercedes-integration-panel")).toBeInTheDocument();
  });

  it("calls stop charging from charging section", async () => {
    const user = userEvent.setup();
    setHash("#laddning");
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Stoppa laddning" })).toBeEnabled();
    });

    await user.click(screen.getByRole("button", { name: "Stoppa laddning" }));

    await waitFor(() => {
      expect(mockStopVehicleCharging).toHaveBeenCalledWith("akarp", 1);
    });
  });

  it("calls Mercedes sync before reloading dashboard data", async () => {
    const user = userEvent.setup();
    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Synkronisera nu/i })).toBeEnabled();
    });

    await user.click(screen.getByRole("button", { name: /Synkronisera nu/i }));

    await waitFor(() => {
      expect(mockSyncVehicles).toHaveBeenCalledWith("akarp");
      expect(mockFetchVehicles).toHaveBeenCalled();
    });
  });

  it("shows disabled message when integration is off", async () => {
    mockFetchVehicleIntegrationStatus.mockResolvedValue({
      ...integration,
      enabled: false,
      commands_enabled: false,
      connection_state: "DISCONNECTED",
      health: "UNHEALTHY",
    });

    render(<VehicleOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByText(/Mercedes me-integrationen är inte aktiverad/i)).toBeInTheDocument();
    });
  });
});
