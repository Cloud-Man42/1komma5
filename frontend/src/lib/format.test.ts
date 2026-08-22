import { describe, expect, it } from "vitest";
import {
  formatEnergy,
  formatMoney,
  formatOre,
  formatPercent,
  formatPower,
  formatRelativeTime,
  formatWatts,
} from "@/lib/format";

describe("formatPower", () => {
  it("formats watts below 1 kW", () => {
    expect(formatPower(850)).toBe("850 W");
    expect(formatPower(-450)).toBe("-450 W");
  });

  it("formats kilowatts with one decimal", () => {
    expect(formatPower(5800)).toBe("5,8 kW");
    expect(formatPower(1500)).toBe("1,5 kW");
  });

  it("handles null and NaN", () => {
    expect(formatPower(null)).toBe("—");
    expect(formatPower(Number.NaN)).toBe("—");
  });
});

describe("formatEnergy", () => {
  it("formats with one decimal", () => {
    expect(formatEnergy(31.84)).toBe("31,8 kWh");
  });
});

describe("formatMoney", () => {
  it("uses 0 decimals for amounts >= 100", () => {
    expect(formatMoney(1234)).toMatch(/1\s?234 kr/);
  });

  it("uses 2 decimals for small amounts", () => {
    expect(formatMoney(18.4)).toMatch(/18,40 kr/);
  });

  it("handles negative values", () => {
    expect(formatMoney(-42)).toMatch(/42,00 kr/);
  });
});

describe("formatPercent", () => {
  it("formats integers without decimal", () => {
    expect(formatPercent(82)).toBe("82 %");
  });

  it("formats one decimal when needed", () => {
    expect(formatPercent(87.5)).toBe("87,5 %");
  });
});

describe("formatOre", () => {
  it("formats öre per kWh", () => {
    expect(formatOre(42.3)).toBe("42,3 öre/kWh");
  });
});

describe("formatRelativeTime", () => {
  const now = new Date("2026-08-22T12:00:00Z").getTime();

  it("formats seconds", () => {
    expect(formatRelativeTime("2026-08-22T11:59:48Z", now)).toBe("12 sek sedan");
  });

  it("formats minutes", () => {
    expect(formatRelativeTime("2026-08-22T11:58:00Z", now)).toBe("2 min sedan");
  });

  it("formats hours", () => {
    expect(formatRelativeTime("2026-08-22T10:00:00Z", now)).toBe("2 tim sedan");
  });
});

describe("formatWatts alias", () => {
  it("delegates to formatPower", () => {
    expect(formatWatts(1500)).toBe("1,5 kW");
  });
});
