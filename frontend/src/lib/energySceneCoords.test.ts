import { describe, expect, it } from "vitest";
import {
  roundSceneCoord,
  screenToViewBoxSlice,
  SCENE_VIEW_H,
  SCENE_VIEW_W,
} from "./energySceneCoords";

describe("energySceneCoords", () => {
  it("rounds to two decimal places", () => {
    expect(roundSceneCoord(45.7777)).toBe(45.78);
    expect(roundSceneCoord(11.074)).toBe(11.07);
  });

  it("maps center of a matching 3:2 rect to viewBox center", () => {
    const rect = { left: 0, top: 0, width: 600, height: 400 };
    const point = screenToViewBoxSlice(rect, 300, 200, SCENE_VIEW_W, SCENE_VIEW_H);
    expect(point.x).toBeCloseTo(50, 1);
    expect(point.y).toBeCloseTo(33.33, 1);
  });

  it("maps top-left of wider container with slice crop", () => {
    const rect = { left: 100, top: 50, width: 800, height: 400 };
    const scale = rect.height / SCENE_VIEW_H;
    const offsetX = (rect.width - SCENE_VIEW_W * scale) / 2;
    const point = screenToViewBoxSlice(rect, 100 + offsetX, 50, SCENE_VIEW_W, SCENE_VIEW_H);
    expect(point.x).toBe(0);
    expect(point.y).toBe(0);
  });

  it("maps top-left of taller container with slice crop", () => {
    const rect = { left: 20, top: 80, width: 400, height: 800 };
    const scale = rect.width / SCENE_VIEW_W;
    const offsetY = (rect.height - SCENE_VIEW_H * scale) / 2;
    const point = screenToViewBoxSlice(rect, 20, 80 + offsetY, SCENE_VIEW_W, SCENE_VIEW_H);
    expect(point.x).toBe(0);
    expect(point.y).toBe(0);
  });
});
