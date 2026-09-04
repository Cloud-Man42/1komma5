import { describe, expect, it } from "vitest";
import { estimateCo2AvoidedKg, formatCo2AvoidedKg } from "./co2SavingsHelpers";

describe("co2SavingsHelpers", () => {
  it("returns null for empty input", () => {
    expect(estimateCo2AvoidedKg(null)).toBeNull();
    expect(estimateCo2AvoidedKg(0)).toBeNull();
  });

  it("estimates avoided co2 from solar kwh", () => {
    expect(estimateCo2AvoidedKg(10)).toBeCloseTo(0.45);
  });

  it("formats grams for small values", () => {
    expect(formatCo2AvoidedKg(0.2)).toBe("200 g");
  });

  it("formats kg for larger values", () => {
    expect(formatCo2AvoidedKg(2.34)).toBe("2.3 kg");
  });
});
