import { describe, expect, it, vi } from "vitest";

import {
  fetchCurrentEvSession,
  fetchEvChargingSessions,
  fetchEvChargingStats,
} from "./api";

describe("ev charging accounting api", () => {
  it("fetchEvChargingStats calls stats endpoint", async () => {
    const mock = {
      period: "month",
      total_energy_kwh: 10,
      actual_cost_sek: 8,
      session_count: 1,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mock,
      }),
    );
    const result = await fetchEvChargingStats("akarp", 1);
    expect(result.total_energy_kwh).toBe(10);
  });

  it("fetchEvChargingSessions returns list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      }),
    );
    const result = await fetchEvChargingSessions("akarp", 1);
    expect(result).toEqual([]);
  });

  it("fetchCurrentEvSession returns null on empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => null,
      }),
    );
    const result = await fetchCurrentEvSession("akarp", 1);
    expect(result).toBeNull();
  });
});
