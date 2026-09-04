import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnergyControlPanel } from "./EnergyControlPanel";
import type { EnergyControlStatus } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchEnergyControlStatus: vi.fn(),
  fetchEnergyControlRecent: vi.fn(),
  updateEnergyControlSettings: vi.fn(),
}));

import {
  fetchEnergyControlRecent,
  fetchEnergyControlStatus,
  updateEnergyControlSettings,
} from "@/lib/api";

const sampleStatus: EnergyControlStatus = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  optimization_mode: "MONITOR_ONLY",
  control_enabled: false,
  writes_allowed: false,
  automatic_allowed: false,
  provider: "noop-dry-run",
  last_action: null,
};

describe("EnergyControlPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchEnergyControlStatus).mockResolvedValue(sampleStatus);
    vi.mocked(fetchEnergyControlRecent).mockResolvedValue({ slug: "akarp", actions: [] });
  });

  it("renders current mode", async () => {
    render(<EnergyControlPanel siteSlug="akarp" />);
    expect(await screen.findByText("Energistyrning")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveValue("MONITOR_ONLY");
    expect(screen.getByText("Aktivt: Monitor only")).toBeInTheDocument();
  });

  it("updates optimization mode", async () => {
    vi.mocked(updateEnergyControlSettings).mockResolvedValue({
      ...sampleStatus,
      optimization_mode: "RECOMMEND",
    });
    render(<EnergyControlPanel siteSlug="akarp" />);
    await screen.findByText("Energistyrning");
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "RECOMMEND" } });
    await waitFor(() => {
      expect(updateEnergyControlSettings).toHaveBeenCalledWith("akarp", {
        optimization_mode: "RECOMMEND",
      });
    });
  });

  it("shows error state", async () => {
    vi.mocked(fetchEnergyControlStatus).mockRejectedValue(new Error("503"));
    render(<EnergyControlPanel siteSlug="akarp" />);
    expect(await screen.findByText(/Kunde inte hämta styrningsstatus/)).toBeInTheDocument();
  });
});
