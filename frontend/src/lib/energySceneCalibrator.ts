import generated from "./energyFlowPaths.generated.json";
import type { ScenePoint, SceneWireId } from "./energyFlowSceneLayout";
import { pointsToPath, wirePointsById } from "./energyFlowSceneLayout";
import { SCENE_VIEWBOX, SCENE_VIEW_H, SCENE_VIEW_W } from "./energySceneCoords";

export const CALIBRATOR_STORAGE_KEY = "energy-scene-calibrator-draft";

export const SCENE_WIRE_IDS: SceneWireId[] = [
  "solar-inverter",
  "inverter-battery",
  "house-feed",
  "grid-lawn",
];

export const WIRE_LABELS: Record<SceneWireId, string> = {
  "solar-inverter": "Sol → Växelriktare",
  "inverter-battery": "Växelriktare ↔ Batteri",
  "house-feed": "→ Hushåll",
  "grid-lawn": "Nät (gräsmatta → dos)",
};

export const WIRE_COLORS: Record<SceneWireId, string> = {
  "solar-inverter": "#3b82f6",
  "inverter-battery": "#ef4444",
  "house-feed": "#60a5fa",
  "grid-lawn": "#f87171",
};

export type CalibratorPaths = Record<SceneWireId, ScenePoint[]>;

export function loadInitialPaths(): CalibratorPaths {
  return {
    "solar-inverter": wirePointsById("solar-inverter").map(clonePoint),
    "inverter-battery": wirePointsById("inverter-battery").map(clonePoint),
    "house-feed": wirePointsById("house-feed").map(clonePoint),
    "grid-lawn": wirePointsById("grid-lawn").map(clonePoint),
  };
}

export function clonePoint(point: ScenePoint): ScenePoint {
  return { x: point.x, y: point.y };
}

export function clonePaths(paths: CalibratorPaths): CalibratorPaths {
  return Object.fromEntries(
    SCENE_WIRE_IDS.map((id) => [id, paths[id].map(clonePoint)]),
  ) as CalibratorPaths;
}

export function deriveEquipment(paths: CalibratorPaths) {
  const solar = paths["solar-inverter"][0] ?? generated.meta.equipment.solar;
  const inverter = paths["solar-inverter"].slice(-1)[0] ?? generated.meta.equipment.inverter;
  const battery = paths["inverter-battery"].slice(-1)[0] ?? generated.meta.equipment.battery;
  const junction =
    paths["inverter-battery"].find(
      (point) => point.y === Math.max(...paths["inverter-battery"].map((p) => p.y)),
    ) ?? generated.meta.equipment.junction;
  const house = paths["house-feed"].slice(-1)[0] ?? generated.meta.equipment.house;
  const gridEnd = paths["grid-lawn"][0] ?? generated.meta.equipment.gridEnd;

  return {
    solar,
    inverter,
    battery,
    junction,
    gridTap: junction,
    house,
    gridEnd,
  };
}

export function buildExportJson(paths: CalibratorPaths) {
  const exportPaths: Record<string, { id: string; points: ScenePoint[]; d: string }> = {};
  for (const id of SCENE_WIRE_IDS) {
    exportPaths[id] = {
      id,
      points: paths[id].map(clonePoint),
      d: pointsToPath(paths[id]),
    };
  }

  return {
    meta: {
      source: "energy-scene-calibrator",
      photo: "public/energy-scene-photo.png",
      viewBox: SCENE_VIEWBOX,
      mode: "user-calibrated",
      extractedAt: new Date().toISOString(),
      equipment: deriveEquipment(paths),
    },
    paths: exportPaths,
  };
}

export function formatPoint(point: ScenePoint): string {
  return `{ x: ${point.x}, y: ${point.y} }`;
}

export function buildSpecSnippet(paths: CalibratorPaths): string {
  const lines = SCENE_WIRE_IDS.flatMap((id) => {
    const pts = paths[id].map((point) => `    ${formatPoint(point)},`).join("\n");
    return [`  "${id}": [`, pts, "  ],"];
  });

  return [
    "export const CABLE_PATHS = {",
    ...lines,
    "};",
  ].join("\n");
}

export function parseStoredPaths(raw: string): CalibratorPaths | null {
  try {
    const parsed = JSON.parse(raw) as Partial<CalibratorPaths>;
    for (const id of SCENE_WIRE_IDS) {
      const points = parsed[id];
      if (!Array.isArray(points) || points.length === 0) return null;
      for (const point of points) {
        if (typeof point?.x !== "number" || typeof point?.y !== "number") return null;
      }
    }
    return clonePaths(parsed as CalibratorPaths);
  } catch {
    return null;
  }
}

export function isValidCalibratorPaths(paths: CalibratorPaths): boolean {
  return SCENE_WIRE_IDS.every((id) => Array.isArray(paths[id]) && paths[id].length >= 2);
}
