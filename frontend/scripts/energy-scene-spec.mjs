/**
 * Canonical cable paths — calibrated from user markup 2026-08-14 + photo scan.
 * viewBox 0 0 100 66.6667 ↔ public/energy-scene-photo.png (1536×1024).
 */
export const VIEW_W = 100;
export const VIEW_H = 66.6667;

const SOLAR_X = 45.77;
const INV_X = 51.17;
const BAT_X = 40.49;
const INV_TOP_Y = 20.31;
const JUNCTION_Y = 34.31;
const SOLAR_TOP_Y = 11.07;

/** User-marked routes on the original facade photo. */
export const CABLE_PATHS = {
  "solar-inverter": [
    { x: SOLAR_X, y: SOLAR_TOP_Y },
    { x: SOLAR_X, y: INV_TOP_Y },
    { x: INV_X, y: INV_TOP_Y },
  ],
  "inverter-battery": [
    { x: INV_X, y: INV_TOP_Y },
    { x: INV_X, y: JUNCTION_Y },
    { x: BAT_X, y: JUNCTION_Y },
    { x: BAT_X, y: INV_TOP_Y },
  ],
  "house-feed": [
    { x: INV_X, y: INV_TOP_Y },
    { x: 57.5, y: 25.5 },
    { x: 63.0, y: 28.5 },
  ],
  "grid-lawn": [
    { x: 53.0, y: 63.5 },
    { x: 49.5, y: 56.0 },
    { x: 45.5, y: 48.0 },
    { x: 43.0, y: 41.0 },
    { x: INV_X, y: JUNCTION_Y },
  ],
};

export const EQUIPMENT = {
  solar: { x: SOLAR_X, y: SOLAR_TOP_Y },
  inverter: { x: INV_X, y: INV_TOP_Y },
  battery: { x: BAT_X, y: INV_TOP_Y },
  junction: { x: INV_X, y: JUNCTION_Y },
  gridTap: { x: INV_X, y: JUNCTION_Y },
  house: { x: 63.0, y: 28.5 },
  gridEnd: { x: 53.0, y: 63.5 },
};

export function pointsToPath(points) {
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
}

export function pathsToGeneratedJson() {
  const paths = {};
  for (const [id, points] of Object.entries(CABLE_PATHS)) {
    paths[id] = { id, points, d: pointsToPath(points) };
  }
  return {
    meta: {
      source: "user-markup-2026-08-14",
      photo: "public/energy-scene-photo.png",
      viewBox: `0 0 ${VIEW_W} ${VIEW_H}`,
      mode: "user-calibrated",
      extractedAt: new Date().toISOString(),
      equipment: EQUIPMENT,
    },
    paths,
  };
}
