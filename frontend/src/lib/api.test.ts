import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ENERGY_BALANCE_HISTORY_MAX_LIMIT,
  fetchChargerFeatureMatrix,
  fetchChargerIntegrationMethods,
  fetchChargerManufacturer,
  fetchEnergyBalanceHistory,
  fetchFinancialStats,
  fetchSitePeaks,
  fetchYearForecast,
  formatWatts,
  isAggregated,
  testEvChargerConnection,
} from "./api";

describe("formatWatts", () => {
  it("formats watts below 1000", () => {
    expect(formatWatts(450)).toBe("450 W");
  });

  it("formats kilowatts at and above 1000", () => {
    expect(formatWatts(1500)).toBe("1.5 kW");
  });

  it("handles negative values", () => {
    expect(formatWatts(-2000)).toBe("-2.0 kW");
  });
});

describe("isAggregated", () => {
  it("detects aggregated readings", () => {
    expect(
      isAggregated({
        bucket_start: "2026-01-01T00:00:00Z",
        recorded_at: "2026-01-01T00:00:00Z",
        solar_production_w: 0,
        consumption_w: 0,
        grid_import_w: 0,
        grid_export_w: 0,
        battery_soc_pct: 0,
        battery_power_w: 0,
      }),
    ).toBe(true);
  });

  it("detects raw readings", () => {
    expect(
      isAggregated({
        recorded_at: "2026-01-01T00:00:00Z",
        solar_production_w: 0,
        consumption_w: 0,
        grid_import_w: 0,
        grid_export_w: 0,
        battery_soc_pct: 0,
        battery_power_w: 0,
      }),
    ).toBe(false);
  });
});

describe("fetchSitePeaks", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests the selected period and year", async () => {
    const response = {
      slug: "akarp",
      timezone: "Europe/Stockholm",
      period: "day" as const,
      peaks: [],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchSitePeaks("akarp", "day", 2026)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/peaks?period=day&year=2026",
      { cache: "no-store" },
    );
  });

  it("throws when the peak request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(fetchSitePeaks("akarp", "year")).rejects.toThrow(
      "Failed to fetch peak values: 503",
    );
  });
});

describe("fetchFinancialStats", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests financial statistics for the selected year", async () => {
    const response = {
      slug: "akarp",
      timezone: "Europe/Stockholm",
      period: "month" as const,
      fallback_purchase_price_sek_kwh: 2,
      export_compensation_sek_kwh: 0.8,
      stats: [],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchFinancialStats("akarp", "month", 2026)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/financial-stats?period=month&year=2026",
      { cache: "no-store" },
    );
  });

  it("throws when financial statistics fail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await expect(fetchFinancialStats("akarp", "year")).rejects.toThrow(
      "Failed to fetch financial statistics: 500",
    );
  });
});

describe("fetchYearForecast", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests the selected forecast year", async () => {
    const response = { slug: "akarp", year: 2027, months: [] };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchYearForecast("akarp", 2027)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/forecast?year=2027",
      { cache: "no-store" },
    );
  });

  it("throws when the forecast request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(fetchYearForecast("akarp", 2027)).rejects.toThrow(
      "Failed to fetch forecast: 503",
    );
  });
});

describe("charger catalog API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests a single manufacturer", async () => {
    const response = { id: "zaptec", name: "Zaptec", model_count: 4 };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchChargerManufacturer("zaptec")).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith("/api/chargers/manufacturers/zaptec", {
      cache: "no-store",
    });
  });

  it("requests the feature matrix", async () => {
    const response = [{ manufacturer: "Zaptec", model: "Go", support: "UNSUPPORTED" }];
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchChargerFeatureMatrix()).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith("/api/chargers/feature-matrix", { cache: "no-store" });
  });

  it("requests integration methods", async () => {
    const response = [{ id: "ZAPTEC_REST", label: "Zaptec Cloud API" }];
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchChargerIntegrationMethods()).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith("/api/chargers/integration-methods", {
      cache: "no-store",
    });
  });

  it("requests saved charger connection test", async () => {
    const response = { success: true, status: "OK", message: "Connected" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(testEvChargerConnection("akarp", 4)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith("/api/sites/akarp/ev-chargers/4/test-connection", {
      method: "POST",
    });
  });

  it("requests energy balance history with pagination", async () => {
    const response = { items: [], total: 0 };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchEnergyBalanceHistory("akarp", 4, 25, 5)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/ev-chargers/4/energy-balance/history?limit=25&offset=5",
      { cache: "no-store" },
    );
  });

  it("clamps the balance history page size to what the API accepts", async () => {
    const response = { items: [], total: 0 };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchEnergyBalanceHistory("akarp", 4, 288, 0)).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/sites/akarp/ev-chargers/4/energy-balance/history?limit=${ENERGY_BALANCE_HISTORY_MAX_LIMIT}&offset=0`,
      { cache: "no-store" },
    );
  });

  it("surfaces a rejected balance history request instead of returning empty data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      text: vi.fn().mockResolvedValue("limit too large"),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchEnergyBalanceHistory("akarp", 4)).rejects.toThrow("limit too large");
  });
});
