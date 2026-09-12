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

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp",
      expect.objectContaining({
        method: "PUT",
        credentials: "include",
        headers: expect.any(Headers),
        body: JSON.stringify({ main_fuse_a: 25, safety_margin_a: 2 }),
      }),
    );
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });
});

describe("controlEvCharger", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends mode, target SoC and deadline to the control endpoint", async () => {
    const response = { id: 1, site_slug: "akarp", name: "Halo" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      controlEvCharger("akarp", 1, {
        charging_mode: "SMART_CHARGE",
        target_soc_pct: 90,
        deadline_at: "2026-08-19T05:00:00.000Z",
      }),
    ).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/ev-chargers/1/control",
      expect.objectContaining({
        method: "PATCH",
        credentials: "include",
        headers: expect.any(Headers),
        body: JSON.stringify({
          charging_mode: "SMART_CHARGE",
          target_soc_pct: 90,
          deadline_at: "2026-08-19T05:00:00.000Z",
        }),
      }),
    );
  });

  it("can clear deadline via control endpoint", async () => {
    const response = { id: 1, site_slug: "akarp", name: "Halo" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(response),
    });
    vi.stubGlobal("fetch", fetchMock);

    await controlEvCharger("akarp", 1, { clear_deadline_at: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites/akarp/ev-chargers/1/control",
      expect.objectContaining({
        method: "PATCH",
        credentials: "include",
        headers: expect.any(Headers),
        body: JSON.stringify({ clear_deadline_at: true }),
      }),
    );
  });
});
