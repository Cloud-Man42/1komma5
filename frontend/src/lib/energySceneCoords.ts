import type { ScenePoint, SceneWireId } from "./energyFlowSceneLayout";

export const SCENE_VIEW_W = 100;
export const SCENE_VIEW_H = 66.6667;
export const SCENE_VIEWBOX = `0 0 ${SCENE_VIEW_W} ${SCENE_VIEW_H}`;

export function roundSceneCoord(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Map screen coords to viewBox units for preserveAspectRatio="xMidYMid slice". */
export function screenToViewBoxSlice(
  rect: { left: number; top: number; width: number; height: number },
  clientX: number,
  clientY: number,
  viewW = SCENE_VIEW_W,
  viewH = SCENE_VIEW_H,
): ScenePoint {
  const viewAspect = viewW / viewH;
  const rectAspect = rect.width / rect.height;

  let scale: number;
  let offsetX: number;
  let offsetY: number;

  if (rectAspect > viewAspect) {
    scale = rect.height / viewH;
    offsetX = (rect.width - viewW * scale) / 2;
    offsetY = 0;
  } else {
    scale = rect.width / viewW;
    offsetX = 0;
    offsetY = (rect.height - viewH * scale) / 2;
  }

  return {
    x: roundSceneCoord((clientX - rect.left - offsetX) / scale),
    y: roundSceneCoord((clientY - rect.top - offsetY) / scale),
  };
}

export function clientToViewBox(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): ScenePoint {
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const matrix = svg.getScreenCTM();
  if (matrix) {
    const mapped = point.matrixTransform(matrix.inverse());
    return {
      x: roundSceneCoord(mapped.x),
      y: roundSceneCoord(mapped.y),
    };
  }

  const rect = svg.getBoundingClientRect();
  return screenToViewBoxSlice(rect, clientX, clientY);
}
