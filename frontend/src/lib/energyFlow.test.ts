import { describe, expect, it } from "vitest";
import {
  advanceFlowDashOffset,
  batteryFlowState,
  computeEnergyFlows,
  computeWireAnimations,
  computeWireFlows,
  EMPTY_STICKY_WIRE_STATE,
  flowAnimationDuration,
  gridFlowState,
  isFlowActive,
  resolveGridMeter,
  stabilizeWireAnimations,
} from "./energyFlow";

describe("gridFlowState", () => {
  it("labels grid import when buying from the grid", () => {
    const state = gridFlowState(857, 0);
    expect(state.mode).toBe("import");
    expect(state.title).toBe("NÄT IMPORT");
    expect(state.signedW).toBe(857);
    expect(state.accent).toBe("#f87171");
  });

  it("labels grid export when selling to the grid", () => {
    const state = gridFlowState(0, 1240);
    expect(state.mode).toBe("export");
    expect(state.title).toBe("EXPORT TILL NÄT");
    expect(state.signedW).toBe(-1240);
    expect(state.accent).toBe("#4ade80");
  });

  it("nets import and export when both directions are briefly reported", () => {
    const state = gridFlowState(900, 500);
    expect(state.mode).toBe("import");
    expect(state.signedW).toBe(400);
  });
});

describe("batteryFlowState", () => {
  it("detects charging and discharging from signed power", () => {
    expect(batteryFlowState(1500).mode).toBe("charging");
    expect(batteryFlowState(-900).mode).toBe("discharging");
    expect(batteryFlowState(10).mode).toBe("idle");
  });
});

describe("computeEnergyFlows", () => {
  it("routes solar surplus to grid export and house", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 5000,
      consumptionW: 1200,
      gridImportW: 0,
      gridExportW: 3000,
      batteryPowerW: 0,
      batterySocPct: 50,
    });
    expect(flows.solarToGrid).toBe(3000);
    expect(flows.solarToHouse).toBe(1200);
    expect(flows.gridToHouse).toBe(0);
    expect(flows.batteryToHouse).toBe(0);
  });

  it("attributes battery charging to solar before grid", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 4000,
      consumptionW: 1500,
      gridImportW: 500,
      gridExportW: 0,
      batteryPowerW: 2000,
      batterySocPct: 40,
    });
    expect(flows.solarToBattery).toBe(2000);
    expect(flows.gridToBattery).toBe(0);
    expect(flows.solarToHouse).toBe(1000);
    expect(flows.gridToHouse).toBe(500);
    expect(flows.batteryToHouse).toBe(0);
  });

  it("shows grid import split between house and battery when charging", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 0,
      consumptionW: 1853,
      gridImportW: 4970,
      gridExportW: 0,
      batteryPowerW: 3117,
      batterySocPct: 2,
    });
    expect(flows.gridToBattery).toBe(3117);
    expect(flows.gridToHouse).toBe(1853);
    expect(flows.batteryToHouse).toBe(0);
    expect(flows.solarToBattery).toBe(0);
  });

  it("shows battery discharge to house with optional grid top-up", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 0,
      consumptionW: 1800,
      gridImportW: 200,
      gridExportW: 0,
      batteryPowerW: -1600,
      batterySocPct: 65,
    });
    expect(flows.batteryToHouse).toBe(1600);
    expect(flows.gridToHouse).toBe(200);
    expect(flows.gridToBattery).toBe(0);
  });

  it("shows battery export to grid when discharging and exporting", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 0,
      consumptionW: 500,
      gridImportW: 0,
      gridExportW: 1200,
      batteryPowerW: -1500,
      batterySocPct: 80,
    });
    expect(flows.batteryToHouse).toBe(500);
    expect(flows.batteryToGrid).toBe(1000);
  });

  it("does not show battery-to-house while battery is charging", () => {
    const flows = computeEnergyFlows({
      solarProductionW: 1000,
      consumptionW: 800,
      gridImportW: 1500,
      gridExportW: 0,
      batteryPowerW: 700,
      batterySocPct: 55,
    });
    expect(flows.solarToBattery).toBe(700);
    expect(flows.gridToBattery).toBe(0);
    expect(flows.batteryToHouse).toBe(0);
    expect(flows.solarToHouse).toBe(300);
    expect(flows.gridToHouse).toBe(500);
  });
});

describe("computeWireFlows", () => {
  it("animates grid import from net meter when buying from grid", () => {
    const values = {
      solarProductionW: 0,
      consumptionW: 1853,
      gridImportW: 4970,
      gridExportW: 0,
      batteryPowerW: 3117,
      batterySocPct: 2,
    };
    const wires = computeWireFlows(values);
    expect(wires.gridImportW).toBe(4970);
    expect(wires.houseFeedW).toBe(1853);
    expect(wires.batteryChargeW).toBe(3117);
    expect(wires.batteryDischargeW).toBe(0);
    expect(wires.gridExportW).toBe(0);
  });

  it("animates battery discharge and grid export from signed meter values", () => {
    const wires = computeWireFlows({
      solarProductionW: 0,
      consumptionW: 500,
      gridImportW: 0,
      gridExportW: 1200,
      batteryPowerW: -1500,
      batterySocPct: 80,
    });
    expect(wires.batteryDischargeW).toBe(1500);
    expect(wires.batteryChargeW).toBe(0);
    expect(wires.houseFeedW).toBe(500);
    expect(wires.gridExportW).toBe(1200);
    expect(wires.gridImportW).toBe(0);
  });

  it("shows no grid animation when neither importing nor exporting", () => {
    const wires = computeWireFlows({
      solarProductionW: 3200,
      consumptionW: 1800,
      gridImportW: 0,
      gridExportW: 0,
      batteryPowerW: 0,
      batterySocPct: 72,
    });
    expect(wires.gridImportW).toBe(0);
    expect(wires.gridExportW).toBe(0);
  });

  it("prefers net grid direction when import and export are both reported", () => {
    expect(resolveGridMeter(3000, 500)).toEqual({ importW: 2500, exportW: 0 });
    expect(resolveGridMeter(200, 900)).toEqual({ importW: 0, exportW: 700 });
  });
});

describe("computeWireAnimations", () => {
  it("emits grid import and export slots on the shared grid-lawn path", () => {
    const importSpecs = computeWireAnimations({
      solarProductionW: 0,
      consumptionW: 1800,
      gridImportW: 2000,
      gridExportW: 0,
      batteryPowerW: 0,
      batterySocPct: 50,
    });
    expect(importSpecs.find((s) => s.slot === "gridImport")).toMatchObject({
      pathKey: "grid-lawn",
      slot: "gridImport",
    });

    const exportSpecs = computeWireAnimations({
      solarProductionW: 5000,
      consumptionW: 1200,
      gridImportW: 0,
      gridExportW: 2000,
      batteryPowerW: 0,
      batterySocPct: 50,
    });
    expect(exportSpecs.find((s) => s.slot === "gridExport")).toMatchObject({
      pathKey: "grid-lawn",
      slot: "gridExport",
    });
  });

  it("returns only active wire slots above threshold", () => {
    const specs = computeWireAnimations({
      solarProductionW: 4000,
      consumptionW: 1200,
      gridImportW: 0,
      gridExportW: 900,
      batteryPowerW: 500,
      batterySocPct: 70,
    });
    expect(specs.every((spec) => spec.watts >= 25)).toBe(true);
    const solar = specs.find((s) => s.slot === "solar");
    const gridExport = specs.find((s) => s.slot === "gridExport");
    const batteryCharge = specs.find((s) => s.slot === "batteryCharge");
    expect(solar?.watts).toBe(4000);
    expect(gridExport?.watts).toBe(900);
    expect(batteryCharge?.watts).toBe(500);
    expect(specs.some((s) => s.slot === "gridImport")).toBe(false);
  });

  it("animates battery charge and discharge as separate slots on shared path", () => {
    const discharge = computeWireAnimations({
      solarProductionW: 0,
      consumptionW: 500,
      gridImportW: 0,
      gridExportW: 1200,
      batteryPowerW: -1500,
      batterySocPct: 80,
    });
    expect(discharge.find((s) => s.slot === "batteryDischarge")).toMatchObject({
      slot: "batteryDischarge",
      pathKey: "inverter-battery",
    });
    expect(discharge.some((s) => s.slot === "batteryCharge")).toBe(false);

    const charge = computeWireAnimations({
      solarProductionW: 1000,
      consumptionW: 800,
      gridImportW: 500,
      gridExportW: 0,
      batteryPowerW: 700,
      batterySocPct: 55,
    });
    expect(charge.find((s) => s.slot === "batteryCharge")).toMatchObject({
      slot: "batteryCharge",
      pathKey: "inverter-battery",
    });
    expect(charge.some((s) => s.slot === "batteryDischarge")).toBe(false);
  });

  it("never runs import and export animations on grid wire at the same time", () => {
    const specs = computeWireAnimations({
      solarProductionW: 0,
      consumptionW: 2500,
      gridImportW: 3000,
      gridExportW: 400,
      batteryPowerW: 0,
      batterySocPct: 50,
    });
    const gridSpecs = specs.filter((spec) => spec.pathKey === "grid-lawn");
    expect(gridSpecs).toHaveLength(1);
    expect(gridSpecs[0]?.slot).toBe("gridImport");
  });

  it("includes solar and house slots when those flows are active", () => {
    const specs = computeWireAnimations({
      solarProductionW: 4000,
      consumptionW: 1200,
      gridImportW: 0,
      gridExportW: 900,
      batteryPowerW: 500,
      batterySocPct: 70,
    });
    expect(specs.find((s) => s.slot === "solar")).toMatchObject({ slot: "solar", pathKey: "solar-inverter" });
    expect(specs.find((s) => s.slot === "house")).toMatchObject({ slot: "house", pathKey: "house-feed" });
  });

  it("returns no grid wire when net meter is idle", () => {
    const specs = computeWireAnimations({
      solarProductionW: 2500,
      consumptionW: 1800,
      gridImportW: 0,
      gridExportW: 0,
      batteryPowerW: 0,
      batterySocPct: 60,
    });
    expect(specs.some((spec) => spec.pathKey === "grid-lawn")).toBe(false);
  });
});

describe("stabilizeWireAnimations", () => {
  it("keeps battery charge direction through brief sign noise", () => {
    const charging = {
      solarProductionW: 1000,
      consumptionW: 800,
      gridImportW: 0,
      gridExportW: 0,
      batteryPowerW: 600,
      batterySocPct: 55,
    };
    const first = stabilizeWireAnimations(charging, EMPTY_STICKY_WIRE_STATE);
    expect(first.specs.find((s) => s.slot === "batteryCharge")).toBeTruthy();

    const noisy = stabilizeWireAnimations(
      { ...charging, batteryPowerW: -40 },
      first.next,
    );
    expect(noisy.specs.find((s) => s.slot === "batteryCharge")).toBeTruthy();
    expect(noisy.specs.some((s) => s.slot === "batteryDischarge")).toBe(false);
  });

  it("flips battery direction only after sustained opposite power", () => {
    const charging = stabilizeWireAnimations(
      {
        solarProductionW: 0,
        consumptionW: 500,
        gridImportW: 0,
        gridExportW: 0,
        batteryPowerW: 700,
        batterySocPct: 80,
      },
      EMPTY_STICKY_WIRE_STATE,
    );
    const discharging = stabilizeWireAnimations(
      {
        solarProductionW: 0,
        consumptionW: 500,
        gridImportW: 0,
        gridExportW: 0,
        batteryPowerW: -1500,
        batterySocPct: 80,
      },
      charging.next,
    );
    expect(discharging.specs.find((s) => s.slot === "batteryDischarge")).toBeTruthy();
    expect(discharging.specs.some((s) => s.slot === "batteryCharge")).toBe(false);
  });

  it("keeps grid export direction through brief import noise", () => {
    const exporting = stabilizeWireAnimations(
      {
        solarProductionW: 5000,
        consumptionW: 1200,
        gridImportW: 0,
        gridExportW: 900,
        batteryPowerW: 0,
        batterySocPct: 50,
      },
      EMPTY_STICKY_WIRE_STATE,
    );
    const noisy = stabilizeWireAnimations(
      {
        solarProductionW: 5000,
        consumptionW: 1200,
        gridImportW: 50,
        gridExportW: 900,
        batteryPowerW: 0,
        batterySocPct: 50,
      },
      exporting.next,
    );
    expect(noisy.specs.find((s) => s.slot === "gridExport")).toBeTruthy();
    expect(noisy.specs.some((s) => s.slot === "gridImport")).toBe(false);
  });
});

describe("flow helpers", () => {
  it("treats small flows as inactive", () => {
    expect(isFlowActive(10)).toBe(false);
    expect(isFlowActive(100)).toBe(true);
  });

  it("speeds up animation slightly with higher wattage but stays calm", () => {
    expect(flowAnimationDuration(100)).toBeGreaterThan(7);
    expect(flowAnimationDuration(6000)).toBeGreaterThan(4);
    expect(flowAnimationDuration(100)).toBeGreaterThan(flowAnimationDuration(6000));
  });

  it("wraps dash offset forward without reversing direction", () => {
    expect(advanceFlowDashOffset(-99, 2)).toBe(-1);
    expect(advanceFlowDashOffset(-99.5, 1)).toBe(-0.5);
    expect(advanceFlowDashOffset(-0.5, 1)).toBe(-1.5);
    const wrapped = advanceFlowDashOffset(-99.9, 0.5);
    expect(wrapped).toBeGreaterThan(-100);
    expect(wrapped).toBeLessThan(0);
  });
});
