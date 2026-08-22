import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createSite,
  deleteSite,
  fetchEvBridgeStatus,
  fetchEvSolarChargingPlan,
  fetchHeartbeatConfig,
  fetchMarketPrices,
  fetchSites,
  fetchSolarAccuracy,
  fetchSolarConfig,
  fetchSolarForecast,
  getApiBaseUrl,
  readApiError,
  saveHeartbeatConfig,
  setEvChargerOverride,
  syncEvChargers,
  updateEvCharger,
  updateSite,
  updateSolarConfig,
} from "./api";
import { makeEvCharger, makeSite, makeSolarConfig } from "../test/fixtures";

function mockFetch(body: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    text: vi.fn().mockResolvedValue(typeof body === "string" ? body : JSON.stringify(body)),
    json: vi.fn().mockResolvedValue(body),
  });
}

describe("readApiError", () => {
  it("returns JSON detail string", async () => {
    const res = {
      status: 422,
      text: async () => JSON.stringify({ detail: "Ogiltig latitud" }),
    } as Response;
    await expect(readApiError(res)).resolves.toBe("Ogiltig latitud");
  });

  it("falls back to raw text when JSON is invalid", async () => {
    const res = {
      status: 500,
      text: async () => "Internal Server Error",
    } as Response;
    await expect(readApiError(res)).resolves.toBe("Internal Server Error");
  });

  it("falls back to HTTP status when body is empty", async () => {
    const res = { status: 503, text: async () => "" } as Response;
    await expect(readApiError(res)).resolves.toBe("HTTP 503");
  });
});

describe("getApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("strips trailing slash from env var", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.example.com/");
    expect(getApiBaseUrl()).toBe("http://api.example.com");
  });

  it("returns empty string in browser when env unset", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("");
  });
});

describe("site CRUD", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchSites returns site list", async () => {
    const sites = [makeSite()];
    vi.stubGlobal("fetch", mockFetch(sites));
    await expect(fetchSites()).resolves.toEqual(sites);
  });

  it("fetchSites throws on failure", async () => {
    vi.stubGlobal("fetch", mockFetch(null, false, 500));
    await expect(fetchSites()).rejects.toThrow("Failed to fetch sites: 500");
  });

  it("createSite posts payload", async () => {
    const created = makeSite({ slug: "new-site" });
    const fetchMock = mockFetch(created, true, 201);
    vi.stubGlobal("fetch", fetchMock);
    await expect(createSite({ slug: "new-site", name: "New", timezone: "UTC" })).resolves.toEqual(
      created,
    );
    expect(fetchMock.mock.calls[0][1]?.method).toBe("POST");
  });

  it("updateSite puts payload", async () => {
    const updated = makeSite({ name: "Updated" });
    vi.stubGlobal("fetch", mockFetch(updated));
    await expect(updateSite("akarp", { name: "Updated" })).resolves.toEqual(updated);
  });

  it("deleteSite calls DELETE", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    vi.stubGlobal("fetch", fetchMock);
    await deleteSite("akarp");
    expect(fetchMock.mock.calls[0][1]?.method).toBe("DELETE");
  });
});

describe("EV API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchEvBridgeStatus returns status", async () => {
    const status = { charger_id: 1, bridge_enabled: true, charging_mode: "SMART_CHARGE" };
    vi.stubGlobal("fetch", mockFetch(status));
    await expect(fetchEvBridgeStatus("akarp", 1)).resolves.toEqual(status);
  });

  it("fetchEvSolarChargingPlan returns plan", async () => {
    const plan = { available: false, explanation_sv: "Ingen energi" };
    vi.stubGlobal("fetch", mockFetch(plan));
    await expect(fetchEvSolarChargingPlan("akarp", 1)).resolves.toEqual(plan);
  });

  it("setEvChargerOverride throws on 422", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        text: vi.fn().mockResolvedValue(JSON.stringify({ detail: "Ogiltiga timmar" })),
      }),
    );
    await expect(setEvChargerOverride("akarp", 1, { hours: 6 })).rejects.toThrow(/Ogiltiga timmar|detail/);
  });

  it("syncEvChargers returns charger list", async () => {
    vi.stubGlobal("fetch", mockFetch([makeEvCharger()]));
    await expect(syncEvChargers("akarp")).resolves.toHaveLength(1);
  });

  it("updateEvCharger throws on 404", async () => {
    vi.stubGlobal("fetch", mockFetch({ detail: "Not found" }, false, 404));
    await expect(updateEvCharger("akarp", 99, { name: "X" })).rejects.toThrow(/Not found|detail/);
  });
});

describe("solar API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchSolarConfig returns config", async () => {
    vi.stubGlobal("fetch", mockFetch(makeSolarConfig()));
    await expect(fetchSolarConfig("akarp")).resolves.toMatchObject({ site_slug: "akarp" });
  });

  it("updateSolarConfig uses readApiError on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        text: vi.fn().mockResolvedValue(JSON.stringify({ detail: "Saknar koordinater" })),
      }),
    );
    await expect(updateSolarConfig("akarp", { enabled: true })).rejects.toThrow("Saknar koordinater");
  });

  it("fetchSolarForecast throws on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        text: vi.fn().mockResolvedValue(JSON.stringify({ detail: "Ingen solprognos" })),
      }),
    );
    await expect(fetchSolarForecast("akarp")).rejects.toThrow("Ingen solprognos");
  });

  it("fetchSolarAccuracy returns metrics", async () => {
    const accuracy = {
      site_slug: "akarp",
      model_version: "solar-forecast-v1",
      mape_7d_pct: 12.5,
      mape_30d_pct: 15.0,
      mae_kwh_30d: 1.2,
      bias_pct_30d: -3.0,
      sample_count_30d: 10,
      historical_samples: 100,
    };
    vi.stubGlobal("fetch", mockFetch(accuracy));
    await expect(fetchSolarAccuracy("akarp")).resolves.toEqual(accuracy);
  });
});

describe("system API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchHeartbeatConfig returns config", async () => {
    const config = { connection_type: "mock", sites: [], dashboard_refresh_seconds: 30 };
    vi.stubGlobal("fetch", mockFetch(config));
    await expect(fetchHeartbeatConfig()).resolves.toEqual(config);
  });

  it("saveHeartbeatConfig throws on validation error", async () => {
    vi.stubGlobal("fetch", mockFetch({ detail: "Host required" }, false, 422));
    await expect(
      saveHeartbeatConfig({ connection_type: "local", host: "", port: 8080 }),
    ).rejects.toThrow();
  });

  it("fetchMarketPrices throws on 503", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        text: vi.fn().mockResolvedValue(""),
      }),
    );
    await expect(fetchMarketPrices("akarp")).rejects.toThrow(/503|Failed to fetch market prices/);
  });
});
