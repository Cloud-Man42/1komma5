/** Visual tones for facade conduit animations (matches user markup). */
export type EnergyFlowTone = "blue" | "red" | "green";

export interface EnergyFlowPalette {
  core: string;
  glow: string;
  wire: string;
  light: string;
}

export const ENERGY_FLOW_PALETTE: Record<EnergyFlowTone, EnergyFlowPalette> = {
  blue: {
    core: "#dbeafe",
    glow: "#3b82f6",
    wire: "#60a5fa",
    light: "#93c5fd",
  },
  red: {
    core: "#fee2e2",
    glow: "#ef4444",
    wire: "#f87171",
    light: "#fca5a5",
  },
  green: {
    core: "#dcfce7",
    glow: "#22c55e",
    wire: "#4ade80",
    light: "#86efac",
  },
};

export type EnergyFlowKind =
  | "solar"
  | "battery-discharge"
  | "battery-charge"
  | "grid-import"
  | "grid-export"
  | "house-consumption";

/** Blue = power into the house. Red = import/battery/solar. Green = grid export on lawn cable. */
export function toneForFlowKind(kind: EnergyFlowKind): EnergyFlowTone {
  if (kind === "house-consumption") return "blue";
  if (kind === "grid-export") return "green";
  return "red";
}

export function paletteForFlowKind(kind: EnergyFlowKind): EnergyFlowPalette {
  return ENERGY_FLOW_PALETTE[toneForFlowKind(kind)];
}
