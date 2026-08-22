import { afterEach, describe, expect, it, vi } from "vitest";
import { controlEvCharger, updateSite } from "./api";

describe("updateSite", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends fuse settings to the site update endpoint", async () => {
    const response = {
      slug: "akarp",
      name: "Åkarp",
      timezone: "Europe/Stockholm",
      main_fuse_a: 25,
      safety_margin_a: 2,
      fallback_purchase_price_sek_kwh: 1.2,
      export_compensation_sek_kwh: 0.6,
      latest_reading: null,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      updateSite("akarp", {
        main_fuse_a: 25,
        safety_margin_a: 2,
      }),
    ).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith("/api/sites/akarp", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ main_fuse_a: 25, safety_margin_a: 2 }),
    });
  });
});

describe("controlEvCharger", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends deadline and energy intent to the control endpoint", async () => {
    const response = { id: 1, site_slug: "akarp", name: "Halo" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      controlEvCharger("akarp", 1, {
        charging_mode: "SMART_CHARGE",
        required_energy_kwh: 22,
        deadline_at: "2026-08-19T05:00:00.000Z",
      }),
    ).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith("/api/sites/akarp/ev-chargers/1/control", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        charging_mode: "SMART_CHARGE",
        required_energy_kwh: 22,
        deadline_at: "2026-08-19T05:00:00.000Z",
      }),
    });
  });

  it("can clear deadline via control endpoint", async () => {
    const response = { id: 1, site_slug: "akarp", name: "Halo" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await controlEvCharger("akarp", 1, { clear_deadline_at: true });

    expect(fetchMock).toHaveBeenCalledWith("/api/sites/akarp/ev-chargers/1/control", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clear_deadline_at: true }),
    });
  });
});
