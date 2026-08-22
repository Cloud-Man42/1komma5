import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnergyFlowDiagram } from "./EnergyFlowDiagram";
import { hydrateEnergySceneConfig, resetEnergySceneConfigStore } from "@/lib/energySceneConfigStore";

vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const reading = {
  recorded_at: "2026-08-13T18:00:00Z",
  solar_production_w: 3200,
  consumption_w: 1800,
  grid_import_w: 0,
  grid_export_w: 900,
  battery_soc_pct: 72,
  battery_power_w: 500,
};

describe("EnergyFlowDiagram", () => {
  beforeEach(async () => {
    resetEnergySceneConfigStore();
    localStorage.clear();
    await hydrateEnergySceneConfig();
  });

  it("renders photorealistic scene with callouts in full mode", async () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    await waitFor(() => {
      expect(screen.getByLabelText("Energiflöde visualisering")).toBeTruthy();
    });
    expect(screen.getAllByText(/Hushåll/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Solenergi/)).toBeTruthy();
    expect(screen.getByText(/Batteriladdning/)).toBeTruthy();
    expect(screen.getByText(/Nätinmatning/)).toBeTruthy();
  });

  it("uses the photorealistic background image", async () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    await waitFor(() => {
      const img = document.querySelector(".energy-flow-photo-img") as HTMLImageElement;
      expect(img).toBeTruthy();
      expect(img.src).toContain("energy-scene-photo.png");
    });
  });

  it("renders compact HUD labels", async () => {
    render(<EnergyFlowDiagram reading={reading} size="compact" />);
    await waitFor(() => {
      expect(screen.getByText("Sol")).toBeTruthy();
    });
    expect(screen.getByText("Hus")).toBeTruthy();
    expect(screen.getByText("Batteri")).toBeTruthy();
    expect(screen.getByText("Nät")).toBeTruthy();
  });

  it("shows active flow legend when power is moving", async () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    await waitFor(() => {
      expect(screen.getByText(/Sol → Växelriktare/)).toBeTruthy();
    });
  });

  it("renders HeartBeat-style pulse overlays for active flows", async () => {
    render(<EnergyFlowDiagram reading={reading} size="full" />);
    await waitFor(() => {
      const pulses = document.querySelectorAll(".energy-wire-flow-glow");
      expect(pulses.length).toBeGreaterThan(0);
    });
    expect(document.querySelectorAll(".energy-wire-flow-track").length).toBeGreaterThan(0);
  });

  it("links to scene customization page", async () => {
    render(<EnergyFlowDiagram reading={reading} size="full" siteSlug="hemma" />);
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /Anpassa scen/i }) as HTMLAnchorElement;
      expect(link.href).toContain("/calibrate?site=hemma");
    });
  });
});
