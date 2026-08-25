import { describe, expect, it } from "vitest";
import { formatOrePerKwh, formatSekAmount, formatSekDecimal, formatSekSigned, toOrePerKwh } from "./prices";

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

  it("formats SEK amounts as decimal kr", () => {
    expect(formatSekDecimal(400.52)).toBe("400,52 kr");
    expect(formatSekDecimal(-125.4)).toBe("125,40 kr");
    expect(formatSekDecimal(1234.5).replace(/\u00a0/g, " ")).toBe("1 234,50 kr");
  });

  it("formats signed SEK amounts", () => {
    expect(formatSekSigned(268.05)).toBe("+268,05 kr");
    expect(formatSekSigned(-125.4)).toBe("−125,40 kr");
    expect(formatSekSigned(0)).toBe("0,00 kr");
    expect(formatSekSigned(0.004)).toBe("0,00 kr");
  });
});