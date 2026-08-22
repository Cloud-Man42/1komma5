"use client";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SolarSiteConfigPanel } from "@/components/SolarSiteConfigPanel";

const mockUpdate = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSolarConfig: vi.fn().mockResolvedValue({
    site_slug: "akarp",
    latitude: null,
    longitude: null,
    installed_peak_power_kw: null,
    azimuth_deg: null,
    tilt_deg: null,
    inverter_max_power_kw: null,
    system_loss_percent: 14,
    enabled: false,
    tilt_estimated: false,
    azimuth_estimated: false,
    complete: false,
  }),
  updateSolarConfig: (...args: unknown[]) => mockUpdate(...args),
}));

describe("SolarSiteConfigPanel", () => {
  it("shows coordinate fields in an expanded section when setup is incomplete", async () => {
    render(<SolarSiteConfigPanel siteSlug="akarp" />);
    expect(await screen.findByText("Solprognos — plats & anläggning")).toBeTruthy();
    expect(screen.getByPlaceholderText("t.ex. 55.6050")).toBeTruthy();
    expect(screen.getByPlaceholderText("t.ex. 13.0038")).toBeTruthy();
    expect(screen.getByText(/Ange anläggningens koordinater/)).toBeTruthy();
  });

  it("submits latitude and longitude", async () => {
    mockUpdate.mockResolvedValueOnce({
      site_slug: "akarp",
      latitude: 55.605,
      longitude: 13.0038,
      installed_peak_power_kw: 8,
      azimuth_deg: 180,
      tilt_deg: 30,
      inverter_max_power_kw: null,
      system_loss_percent: 14,
      enabled: true,
      tilt_estimated: false,
      azimuth_estimated: false,
      complete: true,
    });

    render(<SolarSiteConfigPanel siteSlug="akarp" />);
    await screen.findByPlaceholderText("t.ex. 55.6050");

    fireEvent.change(screen.getByPlaceholderText("t.ex. 55.6050"), {
      target: { value: "55.605" },
    });
    fireEvent.change(screen.getByPlaceholderText("t.ex. 13.0038"), {
      target: { value: "13.0038" },
    });
    fireEvent.change(screen.getByPlaceholderText("t.ex. 8.0"), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Spara solprofil" }));

    expect(mockUpdate).toHaveBeenCalledWith(
      "akarp",
      expect.objectContaining({
        latitude: 55.605,
        longitude: 13.0038,
        installed_peak_power_kw: 8,
      }),
    );
    expect(await screen.findByText("Solprofil sparad.")).toBeTruthy();
  });

  it("shows save error on API failure", async () => {
    mockUpdate.mockRejectedValueOnce(new Error("Valideringsfel"));
    render(<SolarSiteConfigPanel siteSlug="akarp" />);
    await screen.findByPlaceholderText("t.ex. 55.6050");
    fireEvent.click(screen.getByRole("button", { name: "Spara solprofil" }));
    expect(await screen.findByText("Valideringsfel")).toBeTruthy();
  });
});
