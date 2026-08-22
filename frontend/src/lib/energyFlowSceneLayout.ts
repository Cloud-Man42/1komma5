/**
 * Conduit paths for the energy facade scene (see scripts/energy-scene-spec.mjs).
 * Animation geometry is authored to match the generated photo + cable overlay.
 */
import generated from "./energyFlowPaths.generated.json";

export type ScenePoint = { x: number; y: number };

export type SceneWireId =
  | "solar-inverter"
  | "inverter-battery"
  | "grid-lawn"
  | "house-feed";

export interface SceneWire {
  id: SceneWireId;
  d: string;
  points: ScenePoint[];
}

type GeneratedPath = {
  id: string;
  points: ScenePoint[];
  d: string;
};

const GENERATED_PATHS = generated.paths as Record<SceneWireId, GeneratedPath>;

function pathPoints(id: SceneWireId): ScenePoint[] {
  const entry = GENERATED_PATHS[id];
  if (!entry?.points?.length) {
    throw new Error(`Missing extracted path: ${id}`);
  }
  return entry.points.map((p) => ({ x: p.x, y: p.y }));
}

function pathD(id: SceneWireId): string {
  const entry = GENERATED_PATHS[id];
  if (!entry?.d) throw new Error(`Missing extracted path d: ${id}`);
  return entry.d;
}

/** Scene anchors derived from traced path endpoints (for callouts / hub glow). */
export const SCENE_ANCHORS = {
  solar: pathPoints("solar-inverter")[0],
  hub: (() => {
    const invBatt = pathPoints("inverter-battery");
    return invBatt.find((p) => p.y === Math.max(...invBatt.map((q) => q.y))) ?? invBatt[0];
  })(),
  battery: pathPoints("inverter-battery").slice(-1)[0],
  grid: pathPoints("grid-lawn").slice(-1)[0],
  house: pathPoints("house-feed").slice(-1)[0],
} as const;

export const SCENE_POINTS = {
  solarRoof: SCENE_ANCHORS.solar,
  inverterHub: SCENE_ANCHORS.hub,
  batteryLink: SCENE_ANCHORS.battery,
  houseEntry: SCENE_ANCHORS.house,
  gridLawnEnd: SCENE_ANCHORS.grid,
} as const;

export function buildSceneWires(): SceneWire[] {
  return (Object.keys(GENERATED_PATHS) as SceneWireId[]).map((id) => ({
    id,
    d: pathD(id),
    points: pathPoints(id),
  }));
}

export function wirePathById(id: SceneWireId): string {
  return pathD(id);
}

export function wirePointsById(id: SceneWireId): ScenePoint[] {
  return pathPoints(id);
}

export function pointsToPath(points: readonly ScenePoint[]): string {
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
}

/** Flip path direction so flow animation always travels start → end along the geometry. */
export function reversePathPoints(points: readonly ScenePoint[]): ScenePoint[] {
  return [...points].reverse();
}

export function pointDistance(a: ScenePoint, b: ScenePoint): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/** Ensure path[0] is nearest `from` and path[last] is nearest `to` for one-way pulse travel. */
export function orientPathBetween(
  points: readonly ScenePoint[],
  from: ScenePoint,
  to: ScenePoint,
): ScenePoint[] {
  if (points.length < 2) return [...points];

  const start = points[0];
  const end = points[points.length - 1];
  const forwardScore = pointDistance(start, from) + pointDistance(end, to);
  const reverseScore = pointDistance(start, to) + pointDistance(end, from);

  if (reverseScore < forwardScore) {
    return reversePathPoints(points);
  }
  return [...points];
}

export function pathForFlowDirection(
  points: readonly ScenePoint[],
  againstDefaultDirection: boolean,
): string {
  return againstDefaultDirection ? pointsToPath(reversePathPoints(points)) : pointsToPath(points);
}

export function photoToPlane(x: number, y: number, aspect: number): [number, number] {
  return [(x / 100 - 0.5) * aspect * 2, -(y / 66.6667 - 0.5) * 2];
}

export function pathLength(points: readonly ScenePoint[]): number {
  let len = 0;
  for (let i = 1; i < points.length; i++) {
    len += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
  }
  return len;
}

export function densifyPolyline(points: readonly ScenePoint[], samplesPerUnit = 2.5): ScenePoint[] {
  if (points.length < 2) return [...points];

  const dense: ScenePoint[] = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const edgeLen = Math.hypot(b.x - a.x, b.y - a.y);
    const steps = Math.max(2, Math.ceil(edgeLen * samplesPerUnit));
    for (let step = 0; step < steps; step += 1) {
      const t = step / steps;
      dense.push({
        x: a.x + (b.x - a.x) * t,
        y: a.y + (b.y - a.y) * t,
      });
    }
  }
  dense.push({ ...points[points.length - 1] });
  return dense;
}

export function parseSvgPathEndpoints(d: string): ScenePoint[] {
  const tokens = d.trim().match(/[ML]|-?\d*\.?\d+/g);
  if (!tokens) return [];

  const points: ScenePoint[] = [];
  let i = 0;
  while (i < tokens.length) {
    const cmd = tokens[i];
    if (cmd === "M" || cmd === "L") {
      const x = Number(tokens[i + 1]);
      const y = Number(tokens[i + 2]);
      if (!Number.isNaN(x) && !Number.isNaN(y)) {
        points.push({ x, y });
      }
      i += 3;
    } else {
      i += 1;
    }
  }

  return points;
}

export function parseSvgPath(d: string, samplesPerUnit = 2.5): ScenePoint[] {
  return densifyPolyline(parseSvgPathEndpoints(d), samplesPerUnit);
}

export type DirectionMarker = ScenePoint & {
  angleDeg: number;
  progress: number;
};

/**
 * Fixed arrow positions ordered from path start to path end.
 * Lighting these in progress order communicates flow without moving an object
 * through a calibrated dogleg that visually appears to bounce.
 */
export function directionMarkersForPath(pathD: string, count = 8): DirectionMarker[] {
  const points = parseSvgPathEndpoints(pathD);
  if (points.length < 2 || count <= 0) return [];

  return Array.from({ length: count }, (_, index) => {
    const progress = (index + 1) / (count + 1);
    const before = samplePathByProgress(points, Math.max(0, progress - 0.01));
    const point = samplePathByProgress(points, progress);
    const after = samplePathByProgress(points, Math.min(0.9999, progress + 0.01));
    return {
      ...point,
      angleDeg: (Math.atan2(after.y - before.y, after.x - before.x) * 180) / Math.PI,
      progress,
    };
  });
}

export type PulsePathLeg = ScenePoint[];

/** Split a polyline where screen-x (or y) changes direction — each leg is monotonic. */
export function splitPolylineAtAxisReversals(
  points: readonly ScenePoint[],
  axis: "x" | "y" = "x",
): PulsePathLeg[] {
  if (points.length < 2) return points.length ? [[...points]] : [];

  const legs: PulsePathLeg[] = [[{ ...points[0] }]];
  let prevCoord = points[0][axis];
  let prevDir = 0;

  for (let i = 1; i < points.length; i += 1) {
    const point = { ...points[i] };
    const coord = point[axis];
    const delta = coord - prevCoord;

    if (Math.abs(delta) > 0.01) {
      const dir = delta > 0 ? 1 : -1;
      if (prevDir !== 0 && dir !== prevDir) {
        const pivot = { ...points[i - 1] };
        legs[legs.length - 1].push(pivot);
        legs.push([pivot, point]);
      } else {
        legs[legs.length - 1].push(point);
      }
      prevDir = dir;
      prevCoord = coord;
    } else {
      legs[legs.length - 1].push(point);
    }
  }

  return legs.filter((leg) => leg.length >= 2);
}

/** Calibrated lawn cable split into forward-only legs for pulse travel. */
export function lawnPulseLegsFromPath(pathD: string, samplesPerUnit = 3): PulsePathLeg[] {
  const sparse = parseSvgPathEndpoints(pathD);
  return splitPolylineAtAxisReversals(sparse, "x").map((leg) =>
    densifyPolyline(leg, samplesPerUnit),
  );
}

export function sampleLeggedPathByProgress(
  legs: readonly PulsePathLeg[],
  progress: number,
): ScenePoint {
  const clamped = Math.min(1, Math.max(0, progress));
  if (legs.length === 0) return { x: 0, y: 0 };
  if (legs.length === 1) return samplePathByProgress(legs[0], clamped);

  const lengths = legs.map((leg) => pathLength(leg));
  const total = lengths.reduce((sum, len) => sum + len, 0);
  if (total <= 0) return { ...legs[0][0] };

  let remaining = clamped * total;
  for (let i = 0; i < legs.length; i += 1) {
    const legLen = lengths[i];
    if (remaining <= legLen || i === legs.length - 1) {
      const legProgress = legLen > 0 ? remaining / legLen : 0;
      return samplePathByProgress(legs[i], Math.min(1, Math.max(0, legProgress)));
    }
    remaining -= legLen;
  }

  const last = legs[legs.length - 1];
  return { ...last[last.length - 1] };
}

/** Straight source→sink line for pulse travel — avoids doglegs that reverse on screen. */
export function straightPulsePathPoints(pathD: string): ScenePoint[] {
  const endpoints = parseSvgPathEndpoints(pathD);
  if (endpoints.length < 2) return endpoints;
  return [endpoints[0], endpoints[endpoints.length - 1]];
}

export function samplePathByProgress(
  points: readonly ScenePoint[],
  progress: number,
): ScenePoint {
  if (points.length === 0) return { x: 0, y: 0 };
  if (points.length === 1) return { ...points[0] };

  const total = pathLength(points);
  if (total <= 0) return { ...points[0] };

  let target = ((progress % 1) + 1) % 1 * total;
  for (let i = 1; i < points.length; i++) {
    const seg = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
    if (target <= seg) {
      const t = seg > 0 ? target / seg : 0;
      return {
        x: points[i - 1].x + (points[i].x - points[i - 1].x) * t,
        y: points[i - 1].y + (points[i].y - points[i - 1].y) * t,
      };
    }
    target -= seg;
  }
  return { ...points[points.length - 1] };
}
