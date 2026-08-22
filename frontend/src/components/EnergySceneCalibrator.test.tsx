import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { EnergySceneCalibrator } from "./EnergySceneCalibrator";
import { hydrateEnergySceneConfig, resetEnergySceneConfigStore } from "@/lib/energySceneConfigStore";

describe("EnergySceneCalibrator", () => {
  beforeEach(async () => {
    resetEnergySceneConfigStore();
    localStorage.clear();
    await hydrateEnergySceneConfig();
  });

  it("renders wire selectors and calibration scene", async () => {
    render(<EnergySceneCalibrator />);
    await waitFor(() => {
      expect(screen.getByText("Sol → Växelriktare")).toBeTruthy();
    });
    expect(screen.getByText("Nät (gräsmatta → dos)")).toBeTruthy();
    expect(screen.getByLabelText("Kalibreringsyta för energikablar")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Ladda ner JSON/i })).toBeTruthy();
  });

  it("switches active wire when selecting another cable", () => {
    render(<EnergySceneCalibrator />);
    fireEvent.click(screen.getByText("→ Hushåll"));
    expect(screen.getByText(/Aktiva punkter/i)).toBeTruthy();
  });

  it("offers export actions for calibrated paths", () => {
    render(<EnergySceneCalibrator />);
    expect(screen.getByRole("button", { name: /Kopiera spec-snippet/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Ladda ner JSON/i })).toBeTruthy();
  });

  it("toggles between edit and view mode", () => {
    render(<EnergySceneCalibrator />);
    expect(screen.getByText(/Aktiva punkter/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Visningsläge/i }));
    expect(screen.queryByText(/Aktiva punkter/i)).toBeNull();
    expect(screen.getByText(/Visningsläge — kablar och utrustning visas utan redigeringshandtag/i)).toBeTruthy();
  });

  it("shows equipment overlay toggle", () => {
    render(<EnergySceneCalibrator />);
    expect(screen.getByLabelText(/Visa utrustning i scenen/i)).toBeTruthy();
  });

  it("shows equipment and photo customization controls", () => {
    render(<EnergySceneCalibrator />);
    expect(screen.getByText("Bakgrundsbild")).toBeTruthy();
    expect(screen.getByText("Utrustning")).toBeTruthy();
    expect(screen.getByText("Solpaneler")).toBeTruthy();
  });

  it("explains that waypoints are saved automatically for animations", async () => {
    render(<EnergySceneCalibrator />);
    await waitFor(() => {
      expect(screen.getByText(/Sparas automatiskt i webbläsaren och används överallt/i)).toBeTruthy();
    });
  });
});
