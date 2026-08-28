import { describe, expect, it } from "vitest";
import { formatSunTime, getSunTimes } from "@/lib/sunTimes";

describe("sunTimes", () => {
  it("returns formatted sunrise and sunset strings", () => {
    const { sunrise, sunset } = getSunTimes(55.605, 13.004, new Date("2026-08-27T12:00:00Z"));
    expect(formatSunTime(sunrise, "Europe/Stockholm")).toMatch(/\d{2}:\d{2}/);
    expect(formatSunTime(sunset, "Europe/Stockholm")).toMatch(/\d{2}:\d{2}/);
  });
});
