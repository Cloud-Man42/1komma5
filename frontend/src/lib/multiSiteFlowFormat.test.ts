import { describe, expect, it } from "vitest";
import { formatFlowPowerCompact, formatFlowPowerFromKw, formatFlowPowerFromW } from "@/lib/multiSiteFlowFormat";

describe("multiSiteFlowFormat", () => {
  it("formats kW above threshold", () => {
    expect(formatFlowPowerFromKw(3.3)).toBe("3.3 kW");
    expect(formatFlowPowerFromW(1200)).toBe("1.2 kW");
  });

  it("formats watts below 1 kW", () => {
    expect(formatFlowPowerFromW(232)).toBe("232 W");
    expect(formatFlowPowerCompact(0)).toBe("0 W");
  });
});
