import { describe, expect, it } from "vitest";
import generated from "./energyFlowPaths.generated.json";
import {
  buildExportJson,
  buildSpecSnippet,
  isValidCalibratorPaths,
  loadInitialPaths,
  parseStoredPaths,
} from "./energySceneCalibrator";

describe("energySceneCalibrator", () => {
  it("loads four wires from generated JSON", () => {
    const paths = loadInitialPaths();
    expect(Object.keys(paths)).toEqual([
      "solar-inverter",
      "inverter-battery",
      "house-feed",
      "grid-lawn",
    ]);
    expect(paths["solar-inverter"].length).toBeGreaterThanOrEqual(2);
  });

  it("builds export JSON with equipment anchors", () => {
    const paths = loadInitialPaths();
    const exported = buildExportJson(paths);
    expect(exported.meta.mode).toBe("user-calibrated");
    expect(exported.meta.viewBox).toBe("0 0 100 66.6667");
    expect(exported.paths["grid-lawn"].d).toBe(generated.paths["grid-lawn"].d);
    expect(exported.meta.equipment.solar).toEqual(paths["solar-inverter"][0]);
  });

  it("builds spec snippet with cable path blocks", () => {
    const snippet = buildSpecSnippet(loadInitialPaths());
    expect(snippet).toContain('export const CABLE_PATHS = {');
    expect(snippet).toContain('"solar-inverter": [');
    expect(snippet).toContain('"grid-lawn": [');
  });

  it("validates stored draft shape", () => {
    const paths = loadInitialPaths();
    const parsed = parseStoredPaths(JSON.stringify(paths));
    expect(parsed).not.toBeNull();
    expect(isValidCalibratorPaths(parsed!)).toBe(true);
  });

  it("rejects invalid stored draft", () => {
    expect(parseStoredPaths("{")).toBeNull();
    expect(parseStoredPaths(JSON.stringify({ "solar-inverter": [] }))).toBeNull();
    expect(parseStoredPaths(JSON.stringify({ "solar-inverter": [{ x: 1 }] }))).toBeNull();
  });
});
