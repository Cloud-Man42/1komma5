import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EnergyOrchestrationPanel } from "@/components/spa/EnergyOrchestrationPanel";

const mockUpdate = vi.fn().mockResolvedValue({
  site_slug: "akarp",
  loads: [
    {
      load_id: "spa_cleaning",
      name: "Spa cleaning",
      load_type: "spa",
      priority: 55,
      strategy: "SMART",
      window_start: "2026-08-26T10:00:00Z",
      window_end: "2026-08-26T12:00:00Z",
      expected_energy_kwh: 2.8,
      expected_cost_sek: 4.5,
      expected_energy_source: "SOLAR",
      reason_sv: "sol",
      explanation_sv: "Solel",
      dry_run: true,
    },
  ],
});

vi.mock("@/lib/api", () => ({
  fetchEnergyOrchestration: vi.fn().mockResolvedValue({
    site_slug: "akarp",
    loads: [
      {
        load_id: "spa_cleaning",
        name: "Spa cleaning",
        load_type: "spa",
        priority: 50,
        strategy: "SMART",
        window_start: "2026-08-26T10:00:00Z",
        window_end: "2026-08-26T12:00:00Z",
        expected_energy_kwh: 2.8,
        expected_cost_sek: 4.5,
        expected_energy_source: "SOLAR",
        reason_sv: "sol",
        explanation_sv: "Solel",
        dry_run: true,
      },
      {
        load_id: "ev_charger_1",
        name: "EV Halo",
        load_type: "ev",
        priority: 40,
        strategy: "SMART",
        window_start: null,
        window_end: null,
        expected_energy_kwh: null,
        expected_cost_sek: null,
        expected_energy_source: null,
        reason_sv: null,
        explanation_sv: null,
        dry_run: true,
      },
    ],
  }),
  updateEnergyOrchestrationPriorities: (...args: unknown[]) => mockUpdate(...args),
}));

describe("EnergyOrchestrationPanel", () => {
  it("renders loads and saves priorities", async () => {
    const user = userEvent.setup();
    render(<EnergyOrchestrationPanel siteSlug="akarp" />);

    expect(await screen.findByText("Energiordning")).toBeInTheDocument();
    expect(screen.getByText("Spa cleaning")).toBeInTheDocument();
    expect(screen.getByText("EV Halo")).toBeInTheDocument();

    const priorityInputs = screen.getAllByRole("spinbutton");
    await user.clear(priorityInputs[0]);
    await user.type(priorityInputs[0], "55");
    await user.click(screen.getByRole("button", { name: "Spara prioritering" }));

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith("akarp", [
        { load_id: "spa_cleaning", priority: 55 },
        { load_id: "ev_charger_1", priority: 40 },
      ]);
    });
  });
});
