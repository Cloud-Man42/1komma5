import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { EnergyBalanceQualityCard } from "./EnergyBalanceQualityCard";

describe("EnergyBalanceQualityCard", () => {
  it("shows balanced status when energy balance is ok", async () => {
    vi.spyOn(api, "fetchEvChargers").mockResolvedValue([
      {
        id: 4,
        name: "Halo",
        bridge_enabled: true,
      } as api.EvCharger,
    ]);
    vi.spyOn(api, "fetchEnergyBalance").mockResolvedValue({
      status: "ok",
      alignment_delta_seconds: 2,
      flags: [],
    } as api.EnergyBalanceSnapshot);

    render(<EnergyBalanceQualityCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("energy-balance-quality-card")).toHaveTextContent("Balanserad");
    });
  });

  it("shows error when balance fetch fails", async () => {
    vi.spyOn(api, "fetchEvChargers").mockResolvedValue([
      { id: 4, name: "Halo", bridge_enabled: true } as api.EvCharger,
    ]);
    vi.spyOn(api, "fetchEnergyBalance").mockRejectedValue(new Error("503"));

    render(<EnergyBalanceQualityCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("energy-balance-quality-card")).toHaveTextContent("503");
    });
  });

  it("shows empty state without chargers", async () => {
    vi.spyOn(api, "fetchEvChargers").mockResolvedValue([]);
    render(<EnergyBalanceQualityCard slug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("energy-balance-quality-card")).toHaveTextContent(
        "Ingen laddare konfigurerad.",
      );
    });
  });
});
