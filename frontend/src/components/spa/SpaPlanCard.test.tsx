import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SpaPlanCard } from "@/components/spa/SpaPlanCard";

vi.mock("@/lib/api", () => ({
  fetchSpaPlan: vi.fn().mockResolvedValue({
    enabled: true,
    consumer_id: 1,
    load_id: "spa_cleaning",
    strategy: "SMART",
    next_cleaning_start: "2026-08-26T11:20:00Z",
    next_cleaning_end: "2026-08-26T13:20:00Z",
    duration_hours: 2,
    planned_energy_source: "Solel",
    estimated_energy_kwh: 3.1,
    estimated_cost_sek: 0.42,
    baseline_cost_sek: 5.27,
    savings_sek: 4.85,
    explanation_sv: "EMIC har valt 13:20 eftersom solöverskottet förväntas vara högst.",
    reason: "solar_surplus",
    reason_sv: "sol_overskott",
    fallback_from_solar_only: false,
    dry_run: true,
    data_quality: "ESTIMATED",
    daily_windows: [],
    daily_target_hours: 2,
    daily_completed_hours: 0,
    daily_progress_pct: 0,
    planned_starts: 1,
    max_starts_per_day: 2,
    starts_used_today: 0,
    config_summary_sv: null,
    config_validation_warning_sv: null,
    blocks: [],
  }),
}));

describe("SpaPlanCard", () => {
  it("renders plan with Beräknad label", async () => {
    render(<SpaPlanCard siteSlug="akarp" />);
    expect(await screen.findByText("Smart energistyrning")).toBeInTheDocument();
    expect(screen.getByText(/Beräknad energi/)).toBeInTheDocument();
    expect(screen.getByText("Solel")).toBeInTheDocument();
  });

  it("shows explanation when expanded", async () => {
    render(<SpaPlanCard siteSlug="akarp" />);
    await screen.findByText("Smart energistyrning");
    await userEvent.click(screen.getByRole("button", { name: /Varför valde EMIC/ }));
    expect(screen.getByText(/solöverskottet/)).toBeInTheDocument();
  });
});
