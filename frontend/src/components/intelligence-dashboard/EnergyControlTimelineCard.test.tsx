import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EnergyControlTimelineCard } from "./EnergyControlTimelineCard";
import type { EnergyControlRecent } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchEnergyControlRecent: vi.fn(),
}));

import { fetchEnergyControlRecent } from "@/lib/api";

const sample: EnergyControlRecent = {
  slug: "akarp",
  actions: [
    {
      id: 1,
      recorded_at: "2026-09-04T08:00:00Z",
      optimization_mode: "RECOMMEND",
      action: "CHARGE_BATTERY",
      target: "site",
      outcome: "SKIPPED",
      dry_run: true,
      reason: "Monitor only",
    },
  ],
};

describe("EnergyControlTimelineCard", () => {
  it("shows empty state when no actions", async () => {
    vi.mocked(fetchEnergyControlRecent).mockResolvedValue({ slug: "akarp", actions: [] });
    render(<EnergyControlTimelineCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText(/Inga loggade styrningsåtgärder ännu/)).toBeInTheDocument();
    });
  });

  it("renders recent actions", async () => {
    vi.mocked(fetchEnergyControlRecent).mockResolvedValue(sample);
    render(<EnergyControlTimelineCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText("CHARGE_BATTERY")).toBeInTheDocument();
      expect(screen.getByText("SKIPPED")).toBeInTheDocument();
    });
  });

  it("shows error state on API failure", async () => {
    vi.mocked(fetchEnergyControlRecent).mockRejectedValue(new Error("503"));
    render(<EnergyControlTimelineCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText(/Kunde inte hämta styrningslogg/)).toBeInTheDocument();
    });
  });
});
