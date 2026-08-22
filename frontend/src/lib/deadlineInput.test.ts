import { describe, expect, it } from "vitest";
import {
  combineDeadlineLocal,
  formatDeadline,
  parseDeadlineLocal,
  toDatetimeLocalValue,
} from "@/lib/deadlineInput";

describe("deadlineInput", () => {
  it("parses ISO deadline into local date and 24h time parts", () => {
    const iso = "2026-08-21T05:00:00.000Z";
    const parts = parseDeadlineLocal(iso);
    const combined = new Date(`${parts.date}T${parts.time}`);
    expect(combined.toISOString()).toBe(iso);
  });

  it("combines date and time into ISO", () => {
    const iso = combineDeadlineLocal("2026-08-22", "14:30");
    expect(iso).toBeTruthy();
    expect(parseDeadlineLocal(iso).date).toBe("2026-08-22");
    expect(parseDeadlineLocal(iso).time).toBe("14:30");
  });

  it("returns null when date is empty", () => {
    expect(combineDeadlineLocal("", "07:00")).toBeNull();
  });

  it("formats deadline with month name and 24h clock", () => {
    const formatted = formatDeadline("2026-08-21T05:00:00.000Z");
    expect(formatted).toBeTruthy();
    expect(formatted).toMatch(/augusti/i);
    expect(formatted).not.toMatch(/am|pm/i);
  });

  it("keeps legacy datetime-local helper compatible", () => {
    const iso = "2026-08-21T05:00:00.000Z";
    expect(toDatetimeLocalValue(iso)).toBe(`${parseDeadlineLocal(iso).date}T${parseDeadlineLocal(iso).time}`);
  });
});
