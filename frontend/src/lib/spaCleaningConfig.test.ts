import { describe, expect, it } from "vitest";

import {
  buildFilterSummaryClient,
  totalDailyRuntimeHours,
  validateFilterPolicyClient,
} from "@/lib/spaCleaningConfig";

describe("spaCleaningConfig", () => {
  const base = {
    filter_cycles_per_day: 4,
    filter_duration_minutes: 120,
    minimum_cycle_separation_minutes: 60,
    allowed_window_start: "07:00",
    allowed_window_end: "22:00",
  };

  it("builds filter policy summary", () => {
    expect(buildFilterSummaryClient(base)).toContain("4 cykler");
    expect(buildFilterSummaryClient(base)).toContain("8 h totalt");
  });

  it("computes total daily runtime", () => {
    expect(totalDailyRuntimeHours(base)).toBe(8);
  });

  it("flags infeasible window", () => {
    const warning = validateFilterPolicyClient({
      ...base,
      allowed_window_end: "10:00",
    });
    expect(warning).toContain("4 cykler");
  });

  it("accepts default 4×2 h configuration", () => {
    expect(validateFilterPolicyClient(base)).toBeNull();
  });
});
