import { describe, expect, it } from "vitest";
import generated from "./energyFlowPaths.generated.json";
import { deriveEquipment, loadInitialPaths } from "./energySceneCalibrator";
import { wirePathForSlot } from "./energySceneConfig";
import {
  buildSceneWires,
  directionMarkersForPath,
  orientPathBetween,
  parseSvgPath,
  parseSvgPathEndpoints,
  pathForFlowDirection,
  lawnPulseLegsFromPath,
  sampleLeggedPathByProgress,
  splitPolylineAtAxisReversals,
  straightPulsePathPoints,
  photoToPlane,
  pointDistance,
  pointsToPath,
  reversePathPoints,
  SCENE_ANCHORS,
  wirePathById,
  wirePointsById,
} from "./energyFlowSceneLayout";

describe("energyFlowSceneLayout", () => {
  it("builds four user-calibrated facade wire paths", () => {
    const wires = buildSceneWires();
    expect(wires.map((w) => w.id)).toEqual([
      "solar-inverter",
      "inverter-battery",
      "house-feed",
      "grid-lawn",
    ]);
  });

  it("uses user-calibrated paths from scene spec", () => {
    expect(generated.meta.mode).toBe("user-calibrated");
    expect(wirePathById("solar-inverter")).toBe(generated.paths["solar-inverter"].d);
  });

  it("routes solar vertically from roof toward inverter", () => {
    const solar = wirePointsById("solar-inverter");
    expect(solar[0].y).toBeLessThan(solar[1].y);
    expect(solar[solar.length - 1].x).toBeGreaterThan(solar[0].x);
  });

  it("routes battery on inverter junction link", () => {
    const battery = wirePathById("inverter-battery");
    expect(battery).toContain(`${SCENE_ANCHORS.battery.x}`);
  });

  it("routes house consumption toward the facade window", () => {
    const house = wirePointsById("house-feed");
    expect(house[house.length - 1].x).toBeGreaterThan(60);
  });

  it("routes grid from lawn up to junction per user markup", () => {
    const grid = wirePointsById("grid-lawn");
    expect(grid[0].y).toBeGreaterThan(60);
    expect(grid[grid.length - 1].y).toBeCloseTo(SCENE_ANCHORS.hub.y, 0);
  });

  it("maps photo coords to centered plane space", () => {
    const [x, y] = photoToPlane(50, 33.3333, 100 / 66.6667);
    expect(x).toBeCloseTo(0);
    expect(y).toBeCloseTo(0);
  });

  it("parses polyline paths for animation sampling", () => {
    const path = pointsToPath([SCENE_ANCHORS.hub, SCENE_ANCHORS.grid]);
    expect(parseSvgPath(path, 4).length).toBeGreaterThan(2);
  });

  it("reverses path direction for opposite physical flow", () => {
    const points = wirePointsById("grid-lawn");
    const forward = pathForFlowDirection(points, false);
    const backward = pathForFlowDirection(points, true);
    expect(forward).toMatch(/^M 53 63\.5/);
    expect(backward).toMatch(/^M 51\.17 34\.31/);
    expect(reversePathPoints(points)[0]).toEqual(points[points.length - 1]);
  });

  it("orients paths from source anchor toward sink anchor", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const gridPoints = paths["grid-lawn"];

    const importPath = orientPathBetween(gridPoints, anchors.gridEnd, anchors.junction);
    expect(pointDistance(importPath[0], anchors.gridEnd)).toBeLessThan(
      pointDistance(importPath[0], anchors.junction),
    );
    expect(pointDistance(importPath.slice(-1)[0], anchors.junction)).toBeLessThan(
      pointDistance(importPath.slice(-1)[0], anchors.gridEnd),
    );

    const exportPath = orientPathBetween(gridPoints, anchors.junction, anchors.gridEnd);
    expect(pointDistance(exportPath[0], anchors.junction)).toBeLessThan(
      pointDistance(exportPath[0], anchors.gridEnd),
    );

    const reversedBatteryPath = [...paths["inverter-battery"]].reverse();
    const chargePath = orientPathBetween(reversedBatteryPath, anchors.inverter, anchors.battery);
    expect(pointDistance(chargePath[0], anchors.inverter)).toBeLessThan(
      pointDistance(chargePath[0], anchors.battery),
    );
  });

  it("builds slot-oriented wire paths for each flow direction", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const equipment = generated.meta.equipment;

    const solarPath = wirePathForSlot(paths, anchors, "solar");
    expect(solarPath).toMatch(new RegExp(`^M ${equipment.solar.x} ${equipment.solar.y}`));

    const housePath = wirePathForSlot(paths, anchors, "house");
    expect(housePath).toMatch(new RegExp(`^M ${equipment.inverter.x} ${equipment.inverter.y}`));

    const gridImportPath = wirePathForSlot(paths, anchors, "gridImport");
    expect(gridImportPath).toMatch(new RegExp(`^M ${equipment.gridEnd.x} ${equipment.gridEnd.y}`));
    expect(gridImportPath).toContain(String(equipment.junction.y));

    const gridExportPath = wirePathForSlot(paths, anchors, "gridExport");
    expect(gridExportPath).toMatch(new RegExp(`^M ${equipment.junction.x} ${equipment.junction.y}`));
    expect(gridExportPath).toContain(String(equipment.gridEnd.y));

    const batteryChargePath = wirePathForSlot(paths, anchors, "batteryCharge");
    expect(batteryChargePath).toMatch(new RegExp(`^M ${equipment.inverter.x} ${equipment.inverter.y}`));

    const batteryDischargePath = wirePathForSlot(paths, anchors, "batteryDischarge");
    expect(batteryDischargePath).toMatch(new RegExp(`^M ${equipment.battery.x} ${equipment.battery.y}`));
  });

  it("grid-lawn import path reverses screen-x at the lawn corner on the full cable", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const importPath = wirePathForSlot(paths, anchors, "gridImport");
    const points = parseSvgPath(importPath, 0.5);
    let prevX = points[0].x;
    let reversed = false;
    for (let i = 1; i < points.length; i += 1) {
      const dx = points[i].x - prevX;
      if (Math.abs(dx) > 0.05) {
        if (i > 1 && dx > 0 && points[i - 1].x < points[i - 2].x) reversed = true;
        prevX = points[i].x;
      }
    }
    expect(reversed).toBe(true);
  });

  it("straightPulsePathPoints keeps monotonic x for grid import meter→house", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const importPath = wirePathForSlot(paths, anchors, "gridImport");
    const endpoints = parseSvgPathEndpoints(importPath);
    const straight = straightPulsePathPoints(importPath);
    expect(straight).toEqual([endpoints[0], endpoints[endpoints.length - 1]]);
    expect(straight[0].x).toBeGreaterThan(straight[1].x);
  });

  it("lawnPulseLegsFromPath splits grid import at the lawn corner", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const importPath = wirePathForSlot(paths, anchors, "gridImport");
    const legs = lawnPulseLegsFromPath(importPath, 1);
    expect(legs.length).toBe(2);
    expect(legs[0][0]).toEqual(parseSvgPathEndpoints(importPath)[0]);
    expect(legs[1][legs[1].length - 1]).toEqual(
      parseSvgPathEndpoints(importPath)[parseSvgPathEndpoints(importPath).length - 1],
    );
  });

  it("splitPolylineAtAxisReversals makes each grid leg monotonic in x", () => {
    const paths = loadInitialPaths();
    const anchors = deriveEquipment(paths);
    const importPath = wirePathForSlot(paths, anchors, "gridImport");
    const exportPath = wirePathForSlot(paths, anchors, "gridExport");
    const importLegs = splitPolylineAtAxisReversals(parseSvgPathEndpoints(importPath), "x");
    const exportLegs = splitPolylineAtAxisReversals(parseSvgPathEndpoints(exportPath), "x");

    expect(importLegs.length).toBe(2);
    for (let i = 1; i < importLegs[0].length; i += 1) {
      expect(importLegs[0][i].x).toBeLessThanOrEqual(importLegs[0][i - 1].x);
    }
    for (let i = 1; i < importLegs[1].length; i += 1) {
      expect(importLegs[1][i].x).toBeGreaterThanOrEqual(importLegs[1][i - 1].x);
    }

    expect(exportLegs.length).toBe(2);
    for (let i = 1; i < exportLegs[0].length; i += 1) {
      expect(exportLegs[0][i].x).toBeLessThanOrEqual(exportLegs[0][i - 1].x);
    }
    for (let i = 1; i < exportLegs[1].length; i += 1) {
      expect(exportLegs[1][i].x).toBeGreaterThanOrEqual(exportLegs[1][i - 1].x);
    }
  });

  it("orients fixed direction markers from path start to path end", () => {
    const forward = directionMarkersForPath("M 0 0 L 10 0", 3);
    const reverse = directionMarkersForPath("M 10 0 L 0 0", 3);

    expect(forward.map((marker) => marker.x)).toEqual([2.5, 5, 7.5]);
    expect(forward.every((marker) => Math.abs(marker.angleDeg) < 0.001)).toBe(true);
    expect(reverse.map((marker) => marker.x)).toEqual([7.5, 5, 2.5]);
    expect(reverse.every((marker) => Math.abs(Math.abs(marker.angleDeg) - 180) < 0.001)).toBe(true);
  });
});
