import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  FinancialStatsView,
  buildFinanceSummarySentence,
  describeEconomicResult,
} from "./FinancialStatsView";

const { fetchFinancialStatsMock } = vi.hoisted(() => ({
  fetchFinancialStatsMock: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, fetchFinancialStats: fetchFinancialStatsMock };
});

function statsResponse(
  period: "day" | "month" | "year",
  overrides: Partial<{
    solar_savings_sek: number;
    battery_savings_sek: number;
    export_revenue_sek: number;
    grid_import_cost_sek: number;
  }> = {},
) {
  return {
    slug: "akarp",
    timezone: "Europe/Stockholm",
    period,
    fallback_purchase_price_sek_kwh: 2,
    export_compensation_sek_kwh: 0.8,
    stats: [
      {
        period_start:
          period === "day" ? "2026-08-18" : period === "month" ? "2026-08" : "2026",
        solar_self_consumed_kwh: 10,
        battery_self_consumed_kwh: 3,
        exported_kwh: 4,
        imported_kwh: 5,
        solar_savings_sek: 20,
        battery_savings_sek: 6,
        export_revenue_sek: 3.2,
        grid_import_cost_sek: 10,
        market_priced_fraction: 0.75,
        ...overrides,
      },
    ],
  };
}

describe("FinancialStatsView helpers", () => {
  it("describes positive economic result", () => {
    expect(describeEconomicResult(19.2)).toEqual({
      amountLabel: "+19,20 kr",
      statusLabel: "Du ligger 19,20 kr plus",
      detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
      tone: "positive",
      className: "finance-card finance-result finance-result-positive",
    });
  });

  it("describes negative economic result", () => {
    expect(describeEconomicResult(-125.4)).toEqual({
      amountLabel: "−125,40 kr",
      statusLabel: "Din energikostnad efter besparingar är 125,40 kr",
      detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
      tone: "negative",
      className: "finance-card finance-result finance-result-negative",
    });
  });

  it("describes zero economic result", () => {
    expect(describeEconomicResult(0)).toEqual({
      amountLabel: "0,00 kr",
      statusLabel: "Besparingar och kostnader tar ut varandra",
      detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
      tone: "neutral",
      className: "finance-card finance-result finance-result-neutral",
    });
  });

  it("builds summary sentence for positive result", () => {
    expect(buildFinanceSummarySentence(843.78, 575.73, 268.05)).toBe(
      "Du har sparat och tjänat 843,78 kr på sol, batteri och såld el. Under samma period har du köpt el för 575,73 kr. Det ger ett ekonomiskt resultat på +268,05 kr.",
    );
  });
});

describe("FinancialStatsView", () => {
  beforeEach(() => {
    fetchFinancialStatsMock.mockReset();
    fetchFinancialStatsMock.mockImplementation(
      async (_slug: string, period: "day" | "month" | "year") => statsResponse(period),
    );
  });

  it("shows plain-language cards, positive import cost and summary", async () => {
    render(<FinancialStatsView siteSlug="akarp" />);

    expect(await screen.findByText("Solen har sparat")).toBeTruthy();
    expect(screen.getByText("El du sluppit köpa tack vare solel")).toBeTruthy();
    expect(screen.getByText("Batteriet har sparat")).toBeTruthy();
    expect(screen.getByText("Du har tjänat på såld el")).toBeTruthy();
    expect(screen.getByText("El du faktiskt köpt")).toBeTruthy();
    expect(screen.getByText("Sol + batteri + försäljning")).toBeTruthy();
    expect(screen.getByText("Ekonomiskt resultat")).toBeTruthy();
    expect(screen.getByText("20,00 kr")).toBeTruthy();
    expect(screen.getByText("6,00 kr")).toBeTruthy();
    expect(screen.getByText("3,20 kr")).toBeTruthy();
    expect(screen.getByText("10,00 kr")).toBeTruthy();
    expect(screen.getByText("29,20 kr")).toBeTruthy();
    expect(screen.getByText("+19,20 kr")).toBeTruthy();
    expect(screen.getByText("Du ligger 19,20 kr plus")).toBeTruthy();
    expect(screen.getByText("29,20 kr − 10,00 kr = +19,20 kr")).toBeTruthy();
    expect(
      screen.getByText(
        "Du har sparat och tjänat 29,20 kr på sol, batteri och såld el. Under samma period har du köpt el för 10,00 kr. Det ger ett ekonomiskt resultat på +19,20 kr.",
      ),
    ).toBeTruthy();
    expect(screen.getByText(/Heartbeat-timpris används för 75%/)).toBeTruthy();
    expect(screen.queryByText("−10 kr")).toBeNull();
    expect(screen.queryByText("Netto efter köpt el")).toBeNull();
  });

  it("shows negative and zero economic result copy", async () => {
    fetchFinancialStatsMock.mockImplementation(async (_slug, period) =>
      statsResponse(period, {
        solar_savings_sek: 5,
        battery_savings_sek: 0,
        export_revenue_sek: 0,
        grid_import_cost_sek: 20,
      }),
    );

    const { unmount } = render(<FinancialStatsView siteSlug="akarp" />);
    expect(await screen.findByText("Din energikostnad efter besparingar är 15,00 kr")).toBeTruthy();
    expect(screen.getByText("−15,00 kr")).toBeTruthy();
    unmount();

    fetchFinancialStatsMock.mockImplementation(async (_slug, period) =>
      statsResponse(period, {
        solar_savings_sek: 10,
        battery_savings_sek: 0,
        export_revenue_sek: 0,
        grid_import_cost_sek: 10,
      }),
    );
    render(<FinancialStatsView siteSlug="akarp" />);
    expect(
      await screen.findByText("Besparingar och kostnader tar ut varandra"),
    ).toBeTruthy();
  });

  it("uses updated table labels and positive import cost cells", async () => {
    render(<FinancialStatsView siteSlug="akarp" />);
    await screen.findByText("Solen har sparat");

    expect(screen.getByRole("columnheader", { name: "Besparing sol" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Besparing batteri" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Intäkt såld el" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Kostnad köpt el" })).toBeTruthy();
    expect(screen.getAllByText("10 kr").length).toBeGreaterThan(0);
    expect(screen.getAllByText("3 kr 20 öre").length).toBeGreaterThan(0);
  });

  it("switches between daily, monthly and yearly statistics with same labels", async () => {
    render(<FinancialStatsView siteSlug="akarp" />);
    await screen.findByText("Solen har sparat");

    fireEvent.click(screen.getByRole("tab", { name: "Månader" }));
    expect(await screen.findByRole("columnheader", { name: "Månad" })).toBeTruthy();
    expect(screen.getByText("Solen har sparat")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "År" }));
    expect(await screen.findByRole("columnheader", { name: "År" })).toBeTruthy();
    expect(screen.getByText("Ekonomiskt resultat")).toBeTruthy();
    expect(screen.queryByLabelText("Välj statistikår")).toBeNull();
  });

  it("shows API failures", async () => {
    fetchFinancialStatsMock.mockRejectedValue(new Error("Price stats unavailable"));

    render(<FinancialStatsView siteSlug="akarp" />);

    expect((await screen.findByRole("alert")).textContent).toContain("Price stats unavailable");
  });
});
