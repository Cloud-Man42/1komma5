import { describe, expect, it } from "vitest";

import { displayStatusSv } from "@/lib/chargingStatusLabels";

describe("displayStatusSv", () => {
  it("shows externally limited label", () => {
    expect(
      displayStatusSv({ state: "CHARGING_STABLE", reason: "cheap_now", externallyLimited: true }),
    ).toBe("Externt begränsad");
  });

  it("shows smart wait reason", () => {
    expect(displayStatusSv({ reason: "smart_wait_cheaper" })).toBe("Pausad");
  });

  it("shows reducing state", () => {
    expect(displayStatusSv({ state: "REDUCING" })).toBe("Minskar laddström");
  });
});
