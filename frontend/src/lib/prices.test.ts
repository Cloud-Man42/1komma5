import { describe, expect, it } from "vitest";
import { formatOrePerKwh, formatSekAmount, toOrePerKwh } from "./prices";

describe("prices", () => {
  it("converts kr/kWh to öre/kWh", () => {
    expect(toOrePerKwh(2.824)).toBeCloseTo(282.4);
  });

  it("formats öre/kWh for display", () => {
    expect(formatOrePerKwh(0.92638125)).toBe("92.6 öre/kWh");
    expect(formatOrePerKwh(4.04329375)).toBe("404.3 öre/kWh");
  });

  it("formats SEK amounts with kronor and öre", () => {
    expect(formatSekAmount(23.1)).toEqual({ kronor: 23, ore: 10, label: "23 kr 10 öre" });
    expect(formatSekAmount(5)).toEqual({ kronor: 5, ore: 0, label: "5 kr" });
  });
});