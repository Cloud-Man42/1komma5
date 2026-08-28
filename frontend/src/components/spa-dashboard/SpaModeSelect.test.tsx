import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SpaModeSelect } from "./SpaModeSelect";

const mockUpdateSpaControlConfig = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    updateSpaControlConfig: (...args: unknown[]) => mockUpdateSpaControlConfig(...args),
  };
});

describe("SpaModeSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateSpaControlConfig.mockResolvedValue({
      consumer_id: 1,
      strategy: "CHEAPEST",
    });
  });

  it("lists available strategies and saves selection", async () => {
    const user = userEvent.setup();
    const onChanged = vi.fn();
    render(
      <SpaModeSelect
        siteSlug="akarp"
        control={{
          consumer_id: 1,
          smart_control_enabled: true,
          strategy: "SMART",
          dry_run: false,
          shadow_mode: false,
          shadow_mode_until: null,
          min_cleaning_hours_per_day: 2,
          allowed_window_start: "08:00",
          allowed_window_end: "22:00",
          prefer_solar: true,
          allow_battery: true,
          min_battery_soc_pct: 20,
          min_run_minutes: 30,
          min_stop_minutes: 30,
          max_starts_per_day: 2,
          filter_cycles_per_day: 2,
          filter_duration_minutes: 60,
          minimum_cycle_separation_minutes: 60,
          filter_optimization_enabled: true,
          safety_floor_frequency_per_day: 1,
          safety_floor_duration_hours: 1,
          smart_preheat_enabled: false,
          normal_temperature_c: 38,
          max_preheat_temperature_c: 39,
          min_comfort_temperature_c: 36,
          load_priority: 50,
          fixed_schedule_start: null,
          fixed_schedule_end: null,
        }}
        onChanged={onChanged}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "CHEAPEST");

    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith("akarp", { strategy: "CHEAPEST" });
      expect(onChanged).toHaveBeenCalled();
    });
  });

  it("shows error when strategy update fails", async () => {
    mockUpdateSpaControlConfig.mockRejectedValueOnce(new Error("Strategi nekad"));
    const user = userEvent.setup();
    render(
      <SpaModeSelect
        siteSlug="akarp"
        control={{
          consumer_id: 1,
          smart_control_enabled: true,
          strategy: "SMART",
          dry_run: false,
          shadow_mode: false,
          shadow_mode_until: null,
          min_cleaning_hours_per_day: 2,
          allowed_window_start: "08:00",
          allowed_window_end: "22:00",
          prefer_solar: true,
          allow_battery: true,
          min_battery_soc_pct: 20,
          min_run_minutes: 30,
          min_stop_minutes: 30,
          max_starts_per_day: 2,
          filter_cycles_per_day: 2,
          filter_duration_minutes: 60,
          minimum_cycle_separation_minutes: 60,
          filter_optimization_enabled: true,
          safety_floor_frequency_per_day: 1,
          safety_floor_duration_hours: 1,
          smart_preheat_enabled: false,
          normal_temperature_c: 38,
          max_preheat_temperature_c: 39,
          min_comfort_temperature_c: 36,
          load_priority: 50,
          fixed_schedule_start: null,
          fixed_schedule_end: null,
        }}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "SOLAR_ONLY");

    await waitFor(() => {
      expect(screen.getByText("Strategi nekad")).toBeInTheDocument();
    });
  });
});
