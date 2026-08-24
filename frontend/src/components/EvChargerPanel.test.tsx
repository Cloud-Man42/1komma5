import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EvChargerPanel } from "@/components/EvChargerPanel";
import { makeEvCharger } from "@/test/fixtures";

vi.mock("next/image", () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => {
    return <img alt="" {...props} />;
  },
}));

vi.mock("@/lib/useDashboardRefresh", () => ({
  useDashboardRefreshSeconds: () => 30,
}));

vi.mock("@/components/EvChargingAnalytics", () => ({
  EvChargingAnalytics: () => <div>Analytics</div>,
}));

vi.mock("@/components/HaloPowerIndicator", () => ({
  HaloPowerIndicator: () => <div>Power</div>,
}));

const mockFetchEvChargers = vi.fn();
const mockFetchEvBridgeStatus = vi.fn();
const mockFetchEvSolarChargingPlan = vi.fn();
const mockFetchEvChargerSavings = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchEvChargers: (...args: unknown[]) => mockFetchEvChargers(...args),
  fetchEvBridgeStatus: (...args: unknown[]) => mockFetchEvBridgeStatus(...args),
  fetchEvSolarChargingPlan: (...args: unknown[]) => mockFetchEvSolarChargingPlan(...args),
  fetchEvChargerSavings: (...args: unknown[]) => mockFetchEvChargerSavings(...args),
  controlEvCharger: vi.fn(),
  setEvChargerOverride: vi.fn(),
  formatWatts: (w: number) => `${w} W`,
  OVERRIDE_HOURS: [4, 8, 12, 24],
}));

const bridgeStatus = {
  charger_id: 1,
  bridge_enabled: true,
  charging_mode: "SMART_CHARGE",
  active_policy: "SMART",
  ev_target_power_w: null,
  requested_current_a: null,
  applied_current_a: null,
  previous_current_a: null,
  last_heartbeat_data_at: null,
  last_bridge_run_at: null,
  halo_connected: true,
  vehicle_connected: false,
  decision_reason: null,
  discovery_hints: [],
  stale: false,
  override_active: false,
  override_until: null,
};

describe("EvChargerPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchEvChargers.mockResolvedValue([]);
    mockFetchEvBridgeStatus.mockResolvedValue(bridgeStatus);
    mockFetchEvSolarChargingPlan.mockResolvedValue({
      available: false,
      explanation_sv: "Ingen solenergi tillgänglig",
    });
    mockFetchEvChargerSavings.mockResolvedValue({
      has_data: false,
      savings_sek: 0,
    });
  });

  it("shows empty state when no chargers", async () => {
    render(<EvChargerPanel siteSlug="akarp" />);
    expect(await screen.findByText(/Inga laddboxar/i)).toBeTruthy();
  });

  it("shows solar charging plan section for bridge-enabled charger", async () => {
    mockFetchEvChargers.mockResolvedValue([makeEvCharger({ bridge_enabled: true })]);
    render(<EvChargerPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText(/Solprognos \(Smart laddning\)/i)).toBeTruthy();
    });
    await waitFor(() => {
      expect(mockFetchEvSolarChargingPlan).toHaveBeenCalled();
    });
  });

  it("shows empty state when charger load fails before data arrives", async () => {
    mockFetchEvChargers.mockRejectedValue(new Error("API failure"));
    render(<EvChargerPanel siteSlug="akarp" />);
    expect(await screen.findByText(/Inga laddboxar/i)).toBeTruthy();
  });

  it("hides schedule fields when Billigast pris mode is selected", async () => {
    mockFetchEvChargers.mockResolvedValue([
      makeEvCharger({
        bridge_enabled: true,
        charging_mode: "SMART_CHARGE",
        deadline_at: "2026-08-23T07:00:00",
      }),
    ]);
    render(<EvChargerPanel siteSlug="akarp" />);

    expect(await screen.findByLabelText(/Avfärd/i)).toBeTruthy();
    expect(screen.getByText(/Klar senast:/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/Laddningsläge/i), {
      target: { value: "PRICE_CHARGE" },
    });

    await waitFor(() => {
      expect(screen.queryByLabelText(/Avfärd/i)).toBeNull();
    });
    expect(screen.queryByText(/^Klar senast$/i)).toBeNull();
    expect(screen.getByText(/Avfärd och klar senast används inte/i)).toBeTruthy();
  });

  it("no longer asks for an energy need in any mode", async () => {
    mockFetchEvChargers.mockResolvedValue([
      makeEvCharger({ bridge_enabled: true, charging_mode: "SMART_CHARGE" }),
    ]);
    render(<EvChargerPanel siteSlug="akarp" />);

    expect(await screen.findByLabelText(/Avfärd/i)).toBeTruthy();
    expect(screen.queryByLabelText(/Energibehov/i)).toBeNull();
    expect(screen.queryByText(/Energibehov/i)).toBeNull();
  });

  it("describes the solar plan without kWh figures", async () => {
    mockFetchEvChargers.mockResolvedValue([makeEvCharger({ bridge_enabled: true })]);
    mockFetchEvSolarChargingPlan.mockResolvedValue({
      available: true,
      solar_first: true,
      explanation_sv: "Solöverskott väntas 10:00–15:00 innan deadline.",
      expected_solar_window_start: "2026-08-23T08:00:00Z",
      expected_solar_window_end: "2026-08-23T13:00:00Z",
      quality: "HIGH",
      confidence: 0.9,
    });

    render(<EvChargerPanel siteSlug="akarp" />);

    expect(await screen.findByText("Solel först")).toBeTruthy();
    expect(screen.queryByText(/Reserverad solel/i)).toBeNull();
    expect(screen.queryByText(/Planerad nätenergi/i)).toBeNull();
  });

  it("does not show solar plan for price-only bridge status", async () => {
    mockFetchEvChargers.mockResolvedValue([makeEvCharger({ bridge_enabled: true, charging_mode: "PRICE_CHARGE" })]);
    mockFetchEvBridgeStatus.mockResolvedValue({
      ...bridgeStatus,
      charging_mode: "PRICE_CHARGE",
    });
    mockFetchEvSolarChargingPlan.mockResolvedValue({
      available: true,
      explanation_sv: "Solplan ska inte visas",
      solar_first: true,
    });

    render(<EvChargerPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(mockFetchEvSolarChargingPlan).toHaveBeenCalled();
    });
    expect(screen.queryByText(/Solprognos \(Smart laddning\)/i)).toBeNull();
  });

  it("shows heartbeat sync status when enabled", async () => {
    mockFetchEvChargers.mockResolvedValue([
      makeEvCharger({
        bridge_enabled: true,
        heartbeat_sync_enabled: true,
        heartbeat_last_pushed_at: "2026-08-18T10:00:00Z",
        heartbeat_sync_error: "timeout",
      }),
    ]);
    render(<EvChargerPanel siteSlug="akarp" />);
    expect(await screen.findByText(/Heartbeat-synk aktiv/i)).toBeTruthy();
    expect(screen.getByText(/Synkfel: timeout/i)).toBeTruthy();
  });
});
