import { describe, expect, it } from "vitest";
import { pctDelta, yesterdayComparisonLabel } from "./todayComparisonHelpers";

describe("todayComparisonHelpers", () => {
  it("computes positive delta", () => {
    expect(pctDelta(11, 10)).toBe("+10%");
  });

  it("returns null when yesterday is zero", () => {
    expect(pctDelta(5, 0)).toBeNull();
  });

  it("builds comparison label", () => {
    expect(yesterdayComparisonLabel(22, 20)).toBe("Igår: +10%");
  });
});
