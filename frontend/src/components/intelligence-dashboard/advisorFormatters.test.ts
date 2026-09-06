import { describe, expect, it } from "vitest";

import {
  energySourceLabelSv,
  formatConfidence,
  formatPct,
  formatSek,
  formatTimeWindow,
  loadTypeLabelSv,
} from "./advisorFormatters";

describe("advisorFormatters", () => {
  it("formats percentages and confidence", () => {
    expect(formatPct(55.4)).toBe("55 %");
    expect(formatConfidence(0.812)).toBe("81 %");
  });

  it("formats sek values", () => {
    expect(formatSek(5.5)).toBe("5.50 kr");
  });

  it("formats time windows and labels", () => {
    expect(
      formatTimeWindow("2026-09-04T10:00:00Z", "2026-09-04T12:00:00Z", "Europe/Stockholm"),
    ).toMatch(/\d{2}:\d{2}–\d{2}:\d{2}/);
    expect(loadTypeLabelSv("ev")).toBe("Fordon");
    expect(energySourceLabelSv("SOLAR")).toBe("Sol");
  });
});
