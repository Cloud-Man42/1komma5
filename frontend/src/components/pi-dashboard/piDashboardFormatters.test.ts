import { describe, expect, it } from "vitest";
import {
  MISSING,
  ampReading,
  formatClockHms,
  formatDataAge,
  formatDayTime,
  formatDelta,
  formatHeaderDate,
  formatKr,
  formatKrSigned,
  formatNumber,
  formatOre,
  kwReading,
  kwhReading,
  pctReading,
  powerReading,
  sectionText,
  sparklineValues,
  tempReading,
} from "./piDashboardFormatters";

const NBSP = "\u00a0";
const MINUS = "\u2212";
const TZ = "Europe/Stockholm";

describe("formatNumber", () => {
  it("groups thousands with a non-breaking space and keeps a decimal point", () => {
    expect(formatNumber(2846, 0)).toBe(`2${NBSP}846`);
    expect(formatNumber(3.25, 2)).toBe("3.25");
    expect(formatNumber(1234567, 0)).toBe(`1${NBSP}234${NBSP}567`);
  });

  it("renders negatives with a typographic minus", () => {
    expect(formatNumber(-912, 0)).toBe(`${MINUS}912`);
  });
});

describe("readings", () => {
  it("splits value and unit", () => {
    expect(kwReading(3.25)).toEqual({ value: "3.25", unit: "kW" });
    expect(kwhReading(24.7)).toEqual({ value: "24.7", unit: "kWh" });
    expect(pctReading(58.4)).toEqual({ value: "58", unit: "%" });
    expect(ampReading(16)).toEqual({ value: "16.0", unit: "A" });
    expect(tempReading(37.4)).toEqual({ value: "37.4", unit: "°C" });
  });

  it("drops the unit and shows -- when data is missing, so the layout cannot jump", () => {
    for (const reading of [kwReading(null), kwhReading(undefined), pctReading(Number.NaN), ampReading(null)]) {
      expect(reading).toEqual({ value: MISSING, unit: "" });
    }
  });

  it("switches charger power between watts and kilowatts", () => {
    expect(powerReading(0)).toEqual({ value: "0", unit: "W" });
    expect(powerReading(450)).toEqual({ value: "450", unit: "W" });
    expect(powerReading(7400)).toEqual({ value: "7.40", unit: "kW" });
    expect(powerReading(null)).toEqual({ value: MISSING, unit: "" });
  });
});

describe("currency", () => {
  it("formats krona amounts", () => {
    expect(formatKr(2846)).toBe(`2${NBSP}846 kr`);
    expect(formatKr(1.28, 2)).toBe("1.28 kr");
    expect(formatKrSigned(912)).toBe(`+912 kr`);
    expect(formatKrSigned(-912)).toBe(`${MINUS}912 kr`);
    expect(formatOre(200.6)).toBe("200.6 öre/kWh");
  });

  it("returns -- rather than a fake zero", () => {
    expect(formatKr(null)).toBe(MISSING);
    expect(formatKrSigned(undefined)).toBe(MISSING);
    expect(formatOre(null)).toBe(MISSING);
  });
});

describe("formatDelta", () => {
  it("signs and points the arrow by direction", () => {
    expect(formatDelta(38)).toEqual({ text: "↑ +38%", direction: "up" });
    expect(formatDelta(-21)).toEqual({ text: "↓ -21%", direction: "down" });
  });

  it("collapses near-zero change to a flat 0%", () => {
    expect(formatDelta(0.2)).toEqual({ text: "0%", direction: "flat" });
  });

  it("reports missing deltas", () => {
    expect(formatDelta(null)).toEqual({ text: MISSING, direction: "flat" });
    expect(formatDelta(Number.POSITIVE_INFINITY)).toEqual({ text: MISSING, direction: "flat" });
  });
});

describe("clocks and dates", () => {
  it("formats the header clock in the site timezone", () => {
    expect(formatClockHms("2026-08-24T06:08:07Z", TZ)).toBe("08:08:07");
  });

  it("falls back to placeholders for missing or invalid timestamps", () => {
    expect(formatClockHms(null, TZ)).toBe("--:--:--");
    expect(formatClockHms("not-a-date", TZ)).toBe("--:--:--");
    expect(formatDayTime(null, TZ)).toBe(MISSING);
    expect(formatDayTime("not-a-date", TZ)).toBe(MISSING);
  });

  it("formats the panel day/time stamp", () => {
    expect(formatDayTime("2026-08-24T06:00:00Z", TZ)).toBe("24 aug. 08:00");
  });

  it("splits the header stamp into weekday, date and time", () => {
    const stamp = formatHeaderDate(new Date("2026-08-24T06:08:07Z"), TZ);
    expect(stamp.weekday).toBe("måndag");
    expect(stamp.date).toBe("24 aug. 2026");
    expect(stamp.time).toBe("08:08");
  });
});

describe("formatDataAge", () => {
  it("scales the unit to the magnitude of the gap", () => {
    expect(formatDataAge(30)).toBe("under en minut");
    expect(formatDataAge(300)).toBe("5 min");
    expect(formatDataAge(7200)).toBe("2 h");
    expect(formatDataAge(86_400)).toBe("1 dag");
    // The Danish site sat at roughly this age with no Heartbeat mapping.
    expect(formatDataAge(1_446_120)).toBe("16 dagar");
  });

  it("switches unit exactly at the boundaries", () => {
    expect(formatDataAge(59)).toBe("under en minut");
    expect(formatDataAge(60)).toBe("1 min");
    expect(formatDataAge(3599)).toBe("59 min");
    expect(formatDataAge(3600)).toBe("1 h");
    expect(formatDataAge(86_399)).toBe("23 h");
  });

  it("reports nothing rather than inventing an age", () => {
    expect(formatDataAge(null)).toBeNull();
    expect(formatDataAge(undefined)).toBeNull();
    expect(formatDataAge(-5)).toBeNull();
    expect(formatDataAge(Number.NaN)).toBeNull();
    expect(formatDataAge(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("sectionText", () => {
  it("uses the unavailable label when a section reports itself unavailable", () => {
    expect(sectionText(false, "Laddar")).toBe("Data saknas");
    expect(sectionText(false, null, "Ingen data")).toBe("Ingen data");
  });

  it("uses -- for an available section with no value", () => {
    expect(sectionText(true, null)).toBe(MISSING);
    expect(sectionText(true, "")).toBe(MISSING);
  });

  it("passes through a present value", () => {
    expect(sectionText(true, "Laddar")).toBe("Laddar");
  });
});

describe("sparklineValues", () => {
  it("extracts the numeric series", () => {
    const data = {
      sparklines: { solar: { points: [{ value: 1 }, { value: 2 }] } },
    } as never;
    expect(sparklineValues(data, "solar")).toEqual([1, 2]);
  });

  it("returns an empty series for unknown keys or no data", () => {
    expect(sparklineValues(null, "solar")).toEqual([]);
    expect(sparklineValues({ sparklines: {} } as never, "solar")).toEqual([]);
  });
});
