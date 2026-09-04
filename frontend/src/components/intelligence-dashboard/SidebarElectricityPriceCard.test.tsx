import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SidebarElectricityPriceCard } from "@/components/intelligence-dashboard/SidebarElectricityPriceCard";
import type { PricePeriodSnapshot } from "@/lib/api";

const TIMEZONE = "Europe/Stockholm";

function samplePeriods(): PricePeriodSnapshot[] {
  const rows: Array<[string, number]> = [
    ["2026-08-28T00:00:00+02:00", 0.22],
    ["2026-08-28T06:00:00+02:00", 0.35],
    ["2026-08-28T09:00:00+02:00", 0.84],
    ["2026-08-28T14:00:00+02:00", 0.43],
    ["2026-08-28T18:00:00+02:00", 1.87],
  ];
  return rows.map(([period_start, import_price_sek_kwh]) => ({
    period_start,
    period_end: period_start,
    price_area: "SE4",
    currency: "SEK",
    market_price_sek_kwh: import_price_sek_kwh * 0.35,
    import_price_sek_kwh,
    export_price_sek_kwh: 0.39,
    source: "heartbeat",
    quality: "REAL",
    is_estimated: false,
    components: {},
  }));
}

describe("SidebarElectricityPriceCard", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders empty state without prices", () => {
    render(<SidebarElectricityPriceCard periods={null} timezone={TIMEZONE} />);
    expect(screen.getByText("ELPRIS IDAG")).toBeTruthy();
    expect(screen.getByText(/Faktiskt köp · 1komma5/i)).toBeTruthy();
    expect(screen.getByText(/Inga elpriser tillgängliga/i)).toBeTruthy();
  });

  it("renders stats and trend for today import prices in SEK", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-28T09:15:00+02:00"));
    render(<SidebarElectricityPriceCard periods={samplePeriods()} timezone={TIMEZONE} />);
    expect(screen.getByText("22 öre")).toBeTruthy();
    expect(screen.getByText("187 öre")).toBeTruthy();
    expect(screen.getByText("Lägst")).toBeTruthy();
    expect(screen.getByText("Nu")).toBeTruthy();
    expect(screen.getByText("Högst")).toBeTruthy();
    expect(screen.getByTestId("sidebar-elprice-trend")).toBeTruthy();
  });

  it("renders triple price row when strategy is provided", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-28T09:15:00+02:00"));
    render(
      <SidebarElectricityPriceCard
        periods={samplePeriods()}
        timezone={TIMEZONE}
        strategy={{
          slug: "akarp",
          timezone: TIMEZONE,
          period_start: "2026-08-28T07:15:00Z",
          market_price_sek_kwh: 0.32,
          import_price_sek_kwh: 1.21,
          export_price_sek_kwh: 0.39,
          market_quality: "REAL",
          import_quality: "REAL",
          export_quality: "CALCULATED",
          battery_soc_pct: 74,
          strategy_state: "NORMAL_SELF_USE",
          confidence: 0.4,
          reason: "",
          reason_sv: "",
          next_peak_at: null,
          next_peak_import_sek_kwh: null,
          optimization_mode: "MONITOR_ONLY",
          expected_saving_today_sek: null,
          recommended_reserve_soc_pct: null,
          recommended_action: "USE_NOW",
          eov_value_sek_kwh: 1.21,
        }}
      />,
    );
    expect(screen.getByTestId("sidebar-elprice-triple")).toBeTruthy();
    expect(screen.getByText("121 öre")).toBeTruthy();
  });
});
