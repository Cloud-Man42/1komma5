import { describe, expect, it } from "vitest";
import {
  formatOrePerKwh,
  formatSekAmount,
  formatSekDecimal,
  formatSekSigned,
  marketApiPriceToOre,
  marketApiPriceToSekKwh,
  marketPointImportOre,
  marketPointSpotOre,
  priceEngineEurToSekKwh,
  sekKwhToOre,
  toOrePerKwh,
} from "./prices";

describe("prices", () => {
  it("converts SEK/kWh to öre/kWh", () => {
    expect(toOrePerKwh(2.824)).toBeCloseTo(282.4);
  });

  it("converts price-engine EUR/kWh API values to SEK/kWh", () => {
    expect(priceEngineEurToSekKwh(0.2)).toBeCloseTo(2.2, 2);
    expect(sekKwhToOre(priceEngineEurToSekKwh(0.26))).toBe(286);
  });

  it("prefers explicit SEK fields from price-engine API", () => {
    const point = {
      spot_eur_kwh: 0.13,
      all_in_eur_kwh: 0.26,
      spot_sek_kwh: 1.46,
      import_sek_kwh: 2.86,
    };
    expect(marketPointSpotOre(point)).toBe(146);
    expect(marketPointImportOre(point)).toBe(286);
  });

  it("treats legacy SEK magnitudes in *_eur_kwh fields as SEK/kWh", () => {
    expect(marketApiPriceToSekKwh(0.84)).toBe(0.84);
    expect(marketApiPriceToOre(0.84)).toBe(84);
    expect(marketApiPriceToOre(1.87)).toBe(187);
  });

  it("formats SEK prices for display", () => {
    expect(formatOrePerKwh(2.86)).toBe("286.0 öre/kWh");
    expect(formatOrePerKwh(1.46)).toBe("146.0 öre/kWh");
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
