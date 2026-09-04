import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SpaOverview } from "./SpaOverview";

const mockFetchSpaStatus = vi.fn();
const mockFetchSpaEnergyPeriod = vi.fn();
const mockFetchSpaPlan = vi.fn();
const mockFetchSpaControlConfig = vi.fn();
const mockFetchSpaHistory = vi.fn();
const mockFetchSpaEconomics = vi.fn();
const mockFetchSpaHealth = vi.fn();
const mockUpdateSpaControlConfig = vi.fn();
const mockFetchSpaEnergyBreakdown = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSpaStatus: (...args: unknown[]) => mockFetchSpaStatus(...args),
    fetchSpaEnergyPeriod: (...args: unknown[]) => mockFetchSpaEnergyPeriod(...args),
    fetchSpaPlan: (...args: unknown[]) => mockFetchSpaPlan(...args),
    fetchSpaControlConfig: (...args: unknown[]) => mockFetchSpaControlConfig(...args),
    fetchSpaHistory: (...args: unknown[]) => mockFetchSpaHistory(...args),
    fetchSpaEconomics: (...args: unknown[]) => mockFetchSpaEconomics(...args),
    fetchSpaHealth: (...args: unknown[]) => mockFetchSpaHealth(...args),
    updateSpaControlConfig: (...args: unknown[]) => mockUpdateSpaControlConfig(...args),
    fetchSpaEnergyBreakdown: (...args: unknown[]) => mockFetchSpaEnergyBreakdown(...args),
  };
});

describe("SpaOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSpaStatus.mockResolvedValue({
      consumer_id: 1,
      site_slug: "akarp",
      online: true,
      water_temperature_c: 37.8,
      set_temperature_c: 38,
      heater_active: true,
      pump_label: "Pump 1: High",
      filter_status: "Filtering",
      filter_cycle_active: true,
      errors: [],
      current_power_w: 2450,
      power_breakdown: { heater: 2000, pump1: 2100, pump2: 250, circulation: 100 },
      power_note_sv: "",
      last_updated: "2026-08-27T08:00:00Z",
      data_source: "ARCTIC_SPA_REST",
      data_quality: "CALCULATED",
      integration_enabled: true,
    });
    mockFetchSpaEnergyPeriod.mockImplementation(async (_slug, period) => ({
      period,
      energy_kwh: 18.7,
      actual_cost_sek: 4.32,
      solar_kwh: 10,
      battery_kwh: 2,
      grid_kwh: 6.7,
      grid_cost_sek: 4.32,
      solar_value_sek: 8,
      battery_value_sek: 1,
      unknown_kwh: 0,
      has_data: true,
    }));
    mockFetchSpaPlan.mockResolvedValue({
      enabled: true,
      daily_progress_pct: 25,
      next_cleaning_start: "2026-08-27T12:30:00Z",
      explanation_sv: "Plan aktiv.",
      daily_windows: [
        {
          start: "2026-08-27T10:30:00Z",
          end: "2026-08-27T11:27:00Z",
          duration_hours: 0.95,
          energy_source_label_sv: "Solel",
          solar_share_pct: 80,
        },
      ],
      config_summary_sv: "2 filtercykler per dag.",
    });
    mockFetchSpaControlConfig.mockResolvedValue({
      consumer_id: 1,
      strategy: "SMART",
      shadow_mode: true,
      filter_duration_minutes: 57,
      allowed_window_start: "12:00",
      allowed_window_end: "16:00",
    });
    mockFetchSpaHistory.mockResolvedValue({
      period: "day",
      points: [{ timestamp: "2026-08-27T08:00:00Z", power_w: 2000, energy_kwh: 0.5, temperature_c: 38 }],
    });
    mockFetchSpaEconomics.mockResolvedValue({
      period: "today",
      energy_kwh: 18,
      cost_sek: 4.5,
      baseline_cost_sek: 8,
      savings_sek: 3.5,
      solar_share_pct: 60,
      battery_share_pct: 10,
      grid_share_pct: 30,
      data_quality: "MEASURED",
    });
    mockFetchSpaHealth.mockResolvedValue({
      consumer_id: 1,
      api_status: "OK",
      spa_status: "ONLINE",
      polling_status: "OK",
      database_status: "OK",
      samples_last_24h: 10,
      samples_with_power_24h: 10,
      sample_energy_kwh_24h: 18,
      intervals_last_24h: 10,
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
    mockUpdateSpaControlConfig.mockResolvedValue({
      consumer_id: 1,
      strategy: "SOLAR_ONLY",
      filter_duration_minutes: 57,
      allowed_window_start: "12:00",
      allowed_window_end: "16:00",
    });
    mockFetchSpaEnergyBreakdown.mockResolvedValue({
      period: "month",
      granularity: "day",
      rows: [],
      total: { period: "month", energy_kwh: 0, actual_cost_sek: 0, has_data: false },
    });
  });

  it("renders mockup sections with live data", async () => {
    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("spa-overview")).toBeInTheDocument();
    });

    expect(screen.getByText(/SPA – ARCTIC SPA/i)).toBeInTheDocument();
    expect(screen.getByText("KOMPONENTER")).toBeInTheDocument();
    expect(screen.getByText(/FÖRBRUKNING – SENASTE 24 TIMMARNA/i)).toBeInTheDocument();
    expect(screen.getByText("SMART FILTERSCHEMA")).toBeInTheDocument();
    expect(screen.getByText("SNABBKONTROLLER")).toBeInTheDocument();
    expect(screen.getByText("VATTENTEMPERATUR")).toBeInTheDocument();
    expect(document.querySelector(".sdash-tub-frame")).toBeTruthy();
  });

  it("opens sensors and analysis drawers", async () => {
    const user = userEvent.setup();
    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(
      () => {
        expect(screen.getByText(/Visa alla sensorer/i)).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );

    await user.click(screen.getByRole("button", { name: /Visa alla sensorer/i }));
    expect(screen.getByTestId("spa-sensors-panel")).toBeInTheDocument();
    expect(screen.getByText("Vattentemperatur")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Stäng" }));
    await user.click(screen.getByRole("button", { name: /Visa detaljerad analys/i }));
    await waitFor(
      () => {
        expect(screen.getByTestId("spa-detailed-analysis")).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );
  }, 20_000);

  it("opens filter schedule drawer", async () => {
    const user = userEvent.setup();
    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(
      () => {
        expect(screen.getByRole("button", { name: /Visa schema/i })).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );

    await user.click(screen.getByRole("button", { name: /Visa schema/i }));

    await waitFor(
      () => {
        expect(screen.getByTestId("spa-filter-schedule-editor")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /Spara schema/i })).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );
  }, 20_000);

  it("updates spa mode from header select", async () => {
    const user = userEvent.setup();
    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/SPALÄGE/i)).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText(/SPALÄGE/i), "SOLAR_ONLY");
    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith("akarp", { strategy: "SOLAR_ONLY" });
    });
  });

  it("toggles shadow mode from header", async () => {
    mockUpdateSpaControlConfig.mockResolvedValueOnce({
      consumer_id: 1,
      strategy: "SMART",
      shadow_mode: false,
    });
    const user = userEvent.setup();
    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("switch", { name: /Shadow mode/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("switch", { name: /Shadow mode/i }));
    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith("akarp", { shadow_mode: false });
    });
  });

  it("shows disabled message when integration is off", async () => {
    mockFetchSpaStatus.mockResolvedValueOnce({
      integration_enabled: false,
      online: false,
      consumer_id: 1,
      site_slug: "akarp",
      errors: [],
      power_breakdown: {},
      power_note_sv: "",
      data_source: "",
      data_quality: "MISSING",
      pump_label: "",
      heater_active: false,
    });

    render(<SpaOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByText(/inte aktiverad/i)).toBeInTheDocument();
    });
  });
});
