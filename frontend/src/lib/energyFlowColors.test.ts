import { describe, expect, it } from "vitest";
import { paletteForFlowKind, toneForFlowKind } from "./energyFlowColors";

describe("energyFlowColors", () => {
  it("uses blue for house consumption", () => {
    expect(toneForFlowKind("house-consumption")).toBe("blue");
  });

  it("uses red for solar, battery and grid import", () => {
    expect(toneForFlowKind("solar")).toBe("red");
    expect(toneForFlowKind("battery-discharge")).toBe("red");
    expect(toneForFlowKind("battery-charge")).toBe("red");
    expect(toneForFlowKind("grid-import")).toBe("red");
  });

  it("uses green for grid export on the lawn cable", () => {
    expect(toneForFlowKind("grid-export")).toBe("green");
    expect(paletteForFlowKind("grid-export").glow).toBe("#22c55e");
  });

  it("returns distinct palettes for blue and red tones", () => {
    expect(paletteForFlowKind("house-consumption").glow).not.toBe(
      paletteForFlowKind("solar").glow,
    );
  });
});
