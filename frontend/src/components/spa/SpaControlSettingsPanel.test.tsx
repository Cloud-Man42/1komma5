import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { SpaControlSettingsPanel } from "@/components/spa/SpaControlSettingsPanel";

const { mockRunSpaCleaningNow, mockUpdateSpaControlConfig, mockFetchSpaControlConfig, mockFetchSpaPlan } =
  vi.hoisted(() => ({
    mockRunSpaCleaningNow: vi.fn(),
    mockUpdateSpaControlConfig: vi.fn(),
    mockFetchSpaControlConfig: vi.fn(),
    mockFetchSpaPlan: vi.fn(),
  }));

vi.mock("@/lib/api", () => ({
  fetchSpaControlConfig: mockFetchSpaControlConfig,
  updateSpaControlConfig: mockUpdateSpaControlConfig,
  runSpaCleaningNow: mockRunSpaCleaningNow,
  fetchSpaPlan: mockFetchSpaPlan,
}));

const baseConfig = {
  consumer_id: 1,
  smart_control_enabled: true,
  strategy: "SMART",
  dry_run: true,
  shadow_mode: false,
  shadow_mode_until: null,
  min_cleaning_hours_per_day: 8,
  allowed_window_start: "07:00",
  allowed_window_end: "22:00",
  prefer_solar: true,
  allow_battery: true,
  min_battery_soc_pct: 40,
  min_run_minutes: 120,
  min_stop_minutes: 60,
  max_starts_per_day: 4,
  filter_cycles_per_day: 4,
  filter_duration_minutes: 120,
  minimum_cycle_separation_minutes: 60,
  filter_optimization_enabled: true,
  safety_floor_frequency_per_day: 4,
  safety_floor_duration_hours: 2,
  smart_preheat_enabled: false,
  normal_temperature_c: 38,
  max_preheat_temperature_c: 39,
  min_comfort_temperature_c: 37,
  load_priority: 50,
  fixed_schedule_start: null,
  fixed_schedule_end: null,
};

const basePlan = {
  enabled: true,
  consumer_id: 1,
  load_id: "spa_cleaning",
  strategy: "SMART",
  next_cleaning_start: "2026-08-26T11:30:00Z",
  next_cleaning_end: "2026-08-26T13:30:00Z",
  duration_hours: 2,
  planned_energy_source: "Solel",
  estimated_energy_kwh: 3,
  estimated_cost_sek: 5,
  baseline_cost_sek: 8,
  savings_sek: 3,
  explanation_sv: "Plan",
  reason: "smart",
  reason_sv: "smart",
  fallback_from_solar_only: false,
  dry_run: true,
  data_quality: "ESTIMATED",
  blocks: [],
  daily_windows: [
    {
      start: "2026-08-26T07:30:00Z",
      end: "2026-08-26T09:30:00Z",
      duration_hours: 2,
      energy_source_label_sv: "☀ Solel",
      solar_share_pct: 92,
    },
    {
      start: "2026-08-26T11:00:00Z",
      end: "2026-08-26T13:00:00Z",
      duration_hours: 2,
      energy_source_label_sv: "🔋 Batteri + sol",
      solar_share_pct: null,
    },
  ],
  daily_target_hours: 8,
  daily_completed_hours: 2.25,
  daily_progress_pct: 28,
  planned_starts: 4,
  max_starts_per_day: 4,
  starts_used_today: 1,
  config_summary_sv: "summary",
  config_validation_warning_sv: null,
  filter_control_source_sv: "Arctic Spa",
  timing_optimization_source_sv: "EMIC",
  optimization_hint_sv: "EMIC ändrar när de fyra filtercyklerna körs",
  next_cycle_starts_in_minutes: 90,
};

describe("SpaControlSettingsPanel", () => {
  beforeEach(() => {
    mockFetchSpaControlConfig.mockResolvedValue(baseConfig);
    mockFetchSpaPlan.mockResolvedValue(basePlan);
    mockUpdateSpaControlConfig.mockResolvedValue(baseConfig);
  });

  it("renders Arctic Spa baseline and filter policy fields", async () => {
    render(<SpaControlSettingsPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("filter-baseline")).toBeInTheDocument();
    expect(screen.getByText("4 cykler per dygn")).toBeInTheDocument();
    expect(screen.getByText("Smart filteroptimering")).toBeInTheDocument();
    expect(screen.getByText("Filtercykler per dygn")).toBeInTheDocument();
    expect(screen.getByText("Tidsoptimering")).toBeInTheDocument();
  });

  it("shows daily filter plan and progress", async () => {
    render(<SpaControlSettingsPanel siteSlug="akarp" />);
    expect(await screen.findByText("Dagens filterplan")).toBeInTheDocument();
    expect(screen.getByTestId("cleaning-daily-progress")).toHaveTextContent("28 % klart");
    expect(screen.getByText("4 av 4 cykler planerade")).toBeInTheDocument();
    expect(screen.getByTestId("next-filter-cycle")).toBeInTheDocument();
  });

  it("shows validation warning for impossible config", async () => {
    mockFetchSpaControlConfig.mockResolvedValueOnce({
      ...baseConfig,
      allowed_window_end: "10:00",
    });
    render(<SpaControlSettingsPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("cleaning-config-validation")).toBeInTheDocument();
  });

  it("saves filter cycles with synced legacy fields", async () => {
    const user = userEvent.setup();
    render(<SpaControlSettingsPanel siteSlug="akarp" />);
    await screen.findByText("Filtercykler per dygn");
    const inputs = screen.getAllByRole("spinbutton");
    const cycles = inputs.find((el) => (el as HTMLInputElement).value === "4");
    expect(cycles).toBeDefined();
    await user.clear(cycles!);
    await user.type(cycles!, "3");
    await user.click(screen.getByRole("button", { name: "Spara inställningar" }));
    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith(
        "akarp",
        expect.objectContaining({
          filter_cycles_per_day: 3,
          max_starts_per_day: 3,
          min_cleaning_hours_per_day: 6,
        }),
      );
    });
  });
});
