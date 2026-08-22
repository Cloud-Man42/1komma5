import { describe, expect, it } from "vitest";
import { OVERRIDE_HOURS } from "./api";

describe("OVERRIDE_HOURS", () => {
  it("exposes 4, 8, 12 and 24 hour override options", () => {
    expect(OVERRIDE_HOURS).toEqual([4, 8, 12, 24]);
  });
});
