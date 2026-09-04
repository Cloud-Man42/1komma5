import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BestChargeWindowCard } from "./BestChargeWindowCard";

vi.mock("@/lib/api", () => ({
  fetchEnergyStrategyCurrent: vi.fn(),
}));

import { fetchEnergyStrategyCurrent } from "@/lib/api";

describe("BestChargeWindowCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders recommendation window", async () => {
    vi.mocked(fetchEnergyStrategyCurrent).mockResolvedValue({
      slug: "akarp",
      timezone: "Europe/Stockholm",
      ev_recommendations: [
        {
          charger_id: 1,
          charger_name: "Halo",
          window_start: "2026-09-04T00:00:00Z",
          window_end: "2026-09-04T01:00:00Z",
          avg_import_sek_kwh: 0.58,
          current_import_sek_kwh: 1.2,
          estimated_saving_sek: 12.5,
          reason_sv: "Billigaste timmen",
        },
      ],
    } as never);
    render(<BestChargeWindowCard slug="akarp" timezone="Europe/Stockholm" />);
    expect(await screen.findByText(/Billigaste timmen/i)).toBeInTheDocument();
    expect(screen.getByText(/Uppskattad besparing/i)).toBeInTheDocument();
  });
});
