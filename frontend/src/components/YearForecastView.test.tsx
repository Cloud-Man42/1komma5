import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { YearForecastView } from "./YearForecastView";

const { fetchYearForecastMock } = vi.hoisted(() => ({
  fetchYearForecastMock: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, fetchYearForecast: fetchYearForecastMock };
});

const values = {
  solar_self_consumed_kwh: 100,
  battery_self_consumed_kwh: 20,
  exported_kwh: 30,
  imported_kwh: 40,
  solar_savings_sek: 200,
  battery_savings_sek: 40,
  export_revenue_sek: 24,
  grid_import_cost_sek: 80,
  net_sek: 184,
};

function forecastResponse(year: number) {
  return {
    slug: "akarp",
    timezone: "Europe/Stockholm",
    year,
    observed_days: 30,
    confidence: "low" as const,
    uncertainty_pct: 35,
    import_baseline_year: 2025,
    import_baseline_source: "Demo import baseline 2025",
    import_baseline_estimated: true,
    import_baseline_kwh: 1000,
    fallback_purchase_price_sek_kwh: 2,
    export_compensation_sek_kwh: 0.8,
    actual: { ...values, net_sek: 50 },
    forecast: { ...values, net_sek: 134 },
    total: values,
    months: Array.from({ length: 12 }, (_, index) => ({
      month: `${year}-${String(index + 1).padStart(2, "0")}`,
      actual: values,
      forecast: values,
      total: values,
    })),
  };
}

describe("YearForecastView", () => {
  beforeEach(() => {
    fetchYearForecastMock.mockReset();
    fetchYearForecastMock.mockImplementation(async (_slug: string, year: number) =>
      forecastResponse(year),
    );
  });

  it("shows full-year forecast, uncertainty and monthly values", async () => {
    render(<YearForecastView siteSlug="akarp" />);

    expect(await screen.findByText("Osäker")).toBeTruthy();
    expect(screen.getByText("±35%")).toBeTruthy();
    expect(screen.getByText("30 dagar mätdata")).toBeTruthy();
    expect(screen.getByText("Köpt el: 2025 (uppskattad månadsfördelning)")).toBeTruthy();
    expect(screen.getByText(/Demo import baseline 2025/)).toBeTruthy();
    expect(screen.getByText("12%")).toBeTruthy();
    expect(screen.getByText("Sol: 100 kWh")).toBeTruthy();
    expect(screen.getByText("Batteri: 20 kWh")).toBeTruthy();
    expect(screen.getByText("Solen har sparat")).toBeTruthy();
    expect(screen.getByText("Prognostiserat ekonomiskt resultat")).toBeTruthy();
    expect(screen.getByText("Sparat: 240 kr")).toBeTruthy();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("12");
    expect(screen.getAllByText("184 kr").length).toBeGreaterThan(0);
    expect(screen.getByRole("columnheader", { name: "Resultat" })).toBeTruthy();
    expect(screen.getByText("december 2026")).toBeTruthy();
  });

  it("loads the next year selected in the dropdown", async () => {
    render(<YearForecastView siteSlug="akarp" />);
    await screen.findByText("Osäker");

    fireEvent.change(screen.getByLabelText("Välj prognosår"), { target: { value: "2027" } });

    expect(await screen.findByText("januari 2027")).toBeTruthy();
    expect(fetchYearForecastMock).toHaveBeenCalledWith("akarp", 2027);
  });

  it("shows forecast API failures", async () => {
    fetchYearForecastMock.mockRejectedValue(new Error("Forecast unavailable"));

    render(<YearForecastView siteSlug="akarp" />);

    expect((await screen.findByRole("alert")).textContent).toContain("Forecast unavailable");
  });

  it("hides the percentage counter when no historical baseline exists", async () => {
    fetchYearForecastMock.mockResolvedValue({
      ...forecastResponse(2026),
      import_baseline_year: null,
      import_baseline_kwh: null,
    });

    render(<YearForecastView siteSlug="new-site" />);

    await screen.findByText("Osäker");
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
