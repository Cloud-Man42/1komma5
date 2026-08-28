import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PeakValuesView } from "./PeakValuesView";

const { fetchSitePeaksMock } = vi.hoisted(() => ({
  fetchSitePeaksMock: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, fetchSitePeaks: fetchSitePeaksMock };
});

describe("PeakValuesView", () => {
  beforeEach(() => {
    fetchSitePeaksMock.mockReset();
    fetchSitePeaksMock.mockImplementation(
      async (_slug: string, period: "day" | "month" | "year") => {
        if (period === "year") {
          return {
            slug: "akarp",
            timezone: "Europe/Stockholm",
            period,
            peaks: [
              {
                period_start: "2026",
                solar_production_w: 7800,
                consumption_w: 5100,
                battery_charge_w: 3200,
                battery_discharge_w: 2500,
              },
            ],
          };
        }
        return {
          slug: "akarp",
          timezone: "Europe/Stockholm",
          period,
          peaks: [
            {
              period_start: period === "day" ? "2026-08-18" : "2026-08",
              solar_production_w: 7800,
              consumption_w: 5100,
              battery_charge_w: 3200,
              battery_discharge_w: 2500,
            },
          ],
        };
      },
    );
  });

  it("shows daily solar, consumption, charge and discharge peaks", async () => {
    render(<PeakValuesView siteSlug="akarp" />);

    expect((await screen.findAllByText("7.8 kW")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("5.1 kW").length).toBeGreaterThan(0);
    expect(screen.getAllByText("3.2 kW").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2.5 kW").length).toBeGreaterThan(0);
    expect(screen.getByRole("columnheader", { name: "Datum" })).toBeTruthy();
    expect(fetchSitePeaksMock).toHaveBeenCalledWith("akarp", "day", 2026);
  });

  it("switches to monthly and yearly summaries", async () => {
    render(<PeakValuesView siteSlug="akarp" />);
    await screen.findAllByText("7.8 kW");

    fireEvent.click(screen.getByRole("tab", { name: "Månader" }));
    expect(await screen.findByRole("columnheader", { name: "Månad" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "År" }));
    expect(await screen.findByRole("columnheader", { name: "År" })).toBeTruthy();
    expect(screen.queryByLabelText("Välj år")).toBeNull();
  });

  it("shows an error when daily peaks cannot be loaded", async () => {
    fetchSitePeaksMock.mockImplementation(
      async (_slug: string, period: "day" | "month" | "year") => {
        if (period === "year") {
          return { slug: "akarp", timezone: "UTC", period, peaks: [] };
        }
        throw new Error("API unavailable");
      },
    );

    render(<PeakValuesView siteSlug="akarp" />);

    expect((await screen.findByRole("alert")).textContent).toContain("API unavailable");
  });
});
