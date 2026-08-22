import { describe, expect, it } from "vitest";
import {
  advanceLawnDash,
  advanceLawnPulse,
  GRID_LAWN_DASH_OFF,
  GRID_LAWN_DASH_ON,
  GRID_LAWN_TRAVEL,
  INITIAL_LAWN_DASH_STATE,
  lawnDashTravelProgress,
  lawnDashVisibility,
  lawnPulseCycleTiming,
  lawnPulseTravelProgress,
  lawnPulseVisibility,
  shouldResetLawnPulse,
} from "./gridLawnFlow";

describe("gridLawnFlow", () => {
  it("fades out near destination and is invisible while off", () => {
    expect(lawnPulseVisibility(0.5, "running")).toBe(1);
    expect(lawnPulseVisibility(0.9, "running")).toBe(1);
    expect(lawnPulseVisibility(0.98, "running")).toBe(0);
    expect(lawnPulseVisibility(1, "off")).toBe(0);
  });

  it("builds SMIL keyframes with invisible jump at cycle end", () => {
    const timing = lawnPulseCycleTiming(9, 0.65);
    expect(timing.cycleSec).toBeCloseTo(9.65);
    expect(Number(timing.moveEnd)).toBeGreaterThan(0.9);
    expect(Number(timing.jumpEnd)).toBeGreaterThan(Number(timing.moveEnd));
    expect(Number(timing.fadeOut)).toBeLessThan(Number(timing.moveEnd));
  });

  it("stays at destination while off then respawns at source", () => {
    const arrived = advanceLawnPulse(
      { progress: 0.98, phase: "running", pauseRemaining: 0 },
      0.05,
      1,
    );
    expect(arrived.phase).toBe("off");
    expect(arrived.progress).toBe(1);
    expect(lawnPulseTravelProgress(arrived)).toBe(1);
    expect(lawnPulseVisibility(1, "off")).toBe(0);

    const respawn = advanceLawnPulse(arrived, 0.7, 1, 0.6);
    expect(respawn.phase).toBe("running");
    expect(respawn.progress).toBe(0);
    expect(lawnPulseTravelProgress(respawn)).toBe(0);
    expect(lawnPulseVisibility(0, "running")).toBe(0);
  });

  it("moves dash offset one way then resets invisibly", () => {
    expect(GRID_LAWN_DASH_ON + GRID_LAWN_DASH_OFF).toBeGreaterThan(GRID_LAWN_TRAVEL);

    const mid = advanceLawnDash(INITIAL_LAWN_DASH_STATE, 0.5, 1);
    expect(mid.phase).toBe("running");
    expect(mid.offset).toBeLessThan(0);
    expect(mid.offset).toBeGreaterThan(-GRID_LAWN_TRAVEL);
    expect(lawnDashVisibility(mid)).toBeGreaterThan(0);

    const arrived = advanceLawnDash(
      { offset: -GRID_LAWN_TRAVEL + 1, phase: "running", pauseRemaining: 0 },
      0.2,
      1,
    );
    expect(arrived.phase).toBe("off");
    expect(arrived.offset).toBe(-GRID_LAWN_TRAVEL);
    expect(lawnDashTravelProgress(arrived)).toBe(1);
    expect(lawnDashVisibility(arrived)).toBe(0);

    const respawn = advanceLawnDash(arrived, 0.7, 1, 0.6);
    expect(respawn.phase).toBe("running");
    expect(respawn.offset).toBe(0);
    expect(lawnDashTravelProgress(respawn)).toBe(0);
  });

  it("only resets session when path, mode, or active state changes", () => {
    expect(shouldResetLawnPulse("a", "import", "a", "import", true)).toBe(false);
    expect(shouldResetLawnPulse("a", "import", "b", "import", true)).toBe(true);
    expect(shouldResetLawnPulse("a", "import", "a", "export", true)).toBe(true);
    expect(shouldResetLawnPulse("a", "import", "a", "import", false)).toBe(true);
  });
});
