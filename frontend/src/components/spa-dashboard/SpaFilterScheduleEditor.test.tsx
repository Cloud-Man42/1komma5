import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SpaFilterScheduleEditor } from "./SpaFilterScheduleEditor";
import type { SpaControlConfig, SpaPlan } from "@/lib/api";

const mockUpdateSpaControlConfig = vi.fn();
const mockFetchSpaPlan = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    updateSpaControlConfig: (...args: unknown[]) => mockUpdateSpaControlConfig(...args),
    fetchSpaPlan: (...args: unknown[]) => mockFetchSpaPlan(...args),
  };
});

const control: SpaControlConfig = {
  consumer_id: 1,
  smart_control_enabled: true,
  strategy: "SMART",
  dry_run: false,
  shadow_mode: false,
  shadow_mode_until: null,
  min_cleaning_hours_per_day: 2,
  allowed_window_start: "12:00",
  allowed_window_end: "16:00",
  prefer_solar: true,
  allow_battery: true,
  min_battery_soc_pct: 20,
  min_run_minutes: 57,
  min_stop_minutes: 60,
  max_starts_per_day: 2,
  filter_cycles_per_day: 2,
  filter_duration_minutes: 57,
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
};

const plan = {
  enabled: true,
  explanation_sv: "Planerad under soltimmar.",
  daily_windows: [
    {
      start: "2026-08-27T10:30:00Z",
      end: "2026-08-27T11:27:00Z",
      duration_hours: 0.95,
      energy_source_label_sv: "Solel",
      solar_share_pct: 80,
    },
  ],
} as SpaPlan;

describe("SpaFilterScheduleEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateSpaControlConfig.mockResolvedValue({
      ...control,
      filter_cycles_per_day: 3,
    });
    mockFetchSpaPlan.mockResolvedValue(plan);
  });

  it("renders editable fields and planned windows", () => {
    render(<SpaFilterScheduleEditor siteSlug="akarp" plan={plan} control={control} />);
    expect(screen.getByTestId("spa-filter-schedule-editor")).toBeInTheDocument();
    expect(screen.getByLabelText(/Filtercykler per dygn/i)).toHaveValue(2);
    expect(screen.getByText(/Solel/i)).toBeInTheDocument();
  });

  it("saves updated schedule", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    render(<SpaFilterScheduleEditor siteSlug="akarp" plan={plan} control={control} onSaved={onSaved} />);

    await user.clear(screen.getByLabelText(/Filtercykler per dygn/i));
    await user.type(screen.getByLabelText(/Filtercykler per dygn/i), "3");
    await user.clear(screen.getByLabelText(/Tillåten tid — till/i));
    await user.type(screen.getByLabelText(/Tillåten tid — till/i), "20:00");
    await user.click(screen.getByRole("button", { name: /Spara schema/i }));

    await waitFor(
      () => {
        expect(mockUpdateSpaControlConfig).toHaveBeenCalled();
        expect(onSaved).toHaveBeenCalled();
        expect(screen.getByText(/Schemat sparades/i)).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );
  }, 15_000);

  it("blocks save when validation fails", async () => {
    const user = userEvent.setup();
    render(
      <SpaFilterScheduleEditor
        siteSlug="akarp"
        plan={plan}
        control={{
          ...control,
          filter_cycles_per_day: 8,
          filter_duration_minutes: 120,
          allowed_window_start: "12:00",
          allowed_window_end: "13:00",
        }}
      />,
    );

    expect(screen.getByRole("button", { name: /Spara schema/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /Spara schema/i }));
    expect(mockUpdateSpaControlConfig).not.toHaveBeenCalled();
  });

  it("shows fixed schedule warning and applies recommended window", async () => {
    const user = userEvent.setup();
    render(
      <SpaFilterScheduleEditor
        siteSlug="akarp"
        plan={plan}
        control={{ ...control, strategy: "FIXED_SCHEDULE", allowed_window_start: "07:00", allowed_window_end: "22:00" }}
      />,
    );

    expect(screen.getByTestId("fixed-schedule-warning")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Använd rekommenderat fönster/i }));
    expect(screen.getByLabelText(/Fast schema — start/i)).toHaveValue("07:00");
    expect(screen.getByLabelText(/Fast schema — slut/i)).toHaveValue("22:00");
  });
});
