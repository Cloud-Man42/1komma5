import type { Reading } from "./api";

export interface EnergyFlowValues {
  solarProductionW: number;
  consumptionW: number;
  gridImportW: number;
  gridExportW: number;
  batteryPowerW: number;
  batterySocPct: number;
}

/** Positive batteryPowerW = charging, negative = discharging (HeartBeat convention). */
export interface EnergyFlowPaths {
  solarToHouse: number;
  solarToBattery: number;
  solarToGrid: number;
  gridToHouse: number;
  gridToBattery: number;
  batteryToHouse: number;
  batteryToGrid: number;
}

export interface BatteryFlowState {
  chargingW: number;
  dischargingW: number;
  mode: "charging" | "discharging" | "idle";
}

export interface WireFlowValues {
  solarInverterW: number;
  houseFeedW: number;
  batteryChargeW: number;
  batteryDischargeW: number;
  gridImportW: number;
  gridExportW: number;
}

const FLOW_THRESHOLD_W = 25;
/** Hysteresis: keep direction until power drops below this while active. */
const FLOW_SLOT_EXIT_W = 15;
/** Hysteresis: flip direction only when opposite flow exceeds this. */
const FLOW_SLOT_FLIP_W = 80;
/** Normalized path length for SVG flow animation (pathLength attribute). */
export const FLOW_PATH_LENGTH = 100;
/** Bright segment length along normalized SVG flow path. */
export const FLOW_DASH_ON = 14;
export const FLOW_DASH_OFF = FLOW_PATH_LENGTH - FLOW_DASH_ON;

/** Net grid meter when import and export are both reported. */
export function resolveGridMeter(
  gridImportW: number,
  gridExportW: number,
): { importW: number; exportW: number } {
  const importW = Math.max(0, gridImportW);
  const exportW = Math.max(0, gridExportW);
  if (importW >= FLOW_THRESHOLD_W && exportW >= FLOW_THRESHOLD_W) {
    if (importW >= exportW) {
      return { importW: importW - exportW, exportW: 0 };
    }
    return { importW: 0, exportW: exportW - importW };
  }
  return { importW, exportW };
}

export function normalizeFlowValues(values: EnergyFlowValues): EnergyFlowValues {
  const grid = resolveGridMeter(values.gridImportW, values.gridExportW);
  return {
    ...values,
    gridImportW: grid.importW,
    gridExportW: grid.exportW,
  };
}

/** Wire animation wattages for facade cables (meter/sign based, one direction per wire). */
export function computeWireFlows(values: EnergyFlowValues): WireFlowValues {
  const normalized = normalizeFlowValues(values);
  const battery = batteryFlowState(normalized.batteryPowerW);

  return {
    // Sol → växelriktare only, never reversed.
    solarInverterW: normalized.solarProductionW,
    // Växelriktare → hus only, never reversed.
    houseFeedW: normalized.consumptionW,
    // Battery cable: charge OR discharge from signed meter power, never both.
    batteryChargeW: battery.mode === "charging" ? battery.chargingW : 0,
    batteryDischargeW: battery.mode === "discharging" ? battery.dischargingW : 0,
    // Grid cable: import OR export from net meter, never both; idle when neither.
    gridImportW: normalized.gridImportW,
    gridExportW: normalized.gridExportW,
  };
}

export type GridFlowMode = "import" | "export" | "idle";

export interface GridFlowState {
  importW: number;
  exportW: number;
  /** Positive = importing from grid, negative = exporting to grid. */
  signedW: number;
  mode: GridFlowMode;
  title: string;
  directionLabel: string;
  accent: string;
  accentGlow: string;
}

const GRID_IMPORT_ACCENT = "#f87171";
const GRID_IMPORT_GLOW = "#fca5a5";
const GRID_EXPORT_ACCENT = "#4ade80";
const GRID_EXPORT_GLOW = "#86efac";
const GRID_IDLE_ACCENT = "#94a3b8";
const GRID_IDLE_GLOW = "#cbd5e1";

/** Canonical grid meter direction for gauges and labels across EMIC. */
export function gridFlowState(gridImportW: number, gridExportW: number): GridFlowState {
  const { importW, exportW } = resolveGridMeter(gridImportW, gridExportW);
  const signedW = importW > 0 ? importW : exportW > 0 ? -exportW : 0;

  if (signedW > 0) {
    return {
      importW,
      exportW: 0,
      signedW,
      mode: "import",
      title: "NÄT IMPORT",
      directionLabel: "Import från nät",
      accent: GRID_IMPORT_ACCENT,
      accentGlow: GRID_IMPORT_GLOW,
    };
  }

  if (signedW < 0) {
    return {
      importW: 0,
      exportW,
      signedW,
      mode: "export",
      title: "EXPORT TILL NÄT",
      directionLabel: "Export till nät",
      accent: GRID_EXPORT_ACCENT,
      accentGlow: GRID_EXPORT_GLOW,
    };
  }

  return {
    importW: 0,
    exportW: 0,
    signedW: 0,
    mode: "idle",
    title: "NÄT",
    directionLabel: "Vila",
    accent: GRID_IDLE_ACCENT,
    accentGlow: GRID_IDLE_GLOW,
  };
}

export function batteryFlowState(batteryPowerW: number): BatteryFlowState {
  if (batteryPowerW >= FLOW_THRESHOLD_W) {
    return { chargingW: batteryPowerW, dischargingW: 0, mode: "charging" };
  }
  if (batteryPowerW <= -FLOW_THRESHOLD_W) {
    return { chargingW: 0, dischargingW: -batteryPowerW, mode: "discharging" };
  }
  return { chargingW: 0, dischargingW: 0, mode: "idle" };
}

/**
 * Allocate flows from measured site values.
 * Battery sign and grid import/export are treated as source of truth.
 */
export function computeEnergyFlows(reading: EnergyFlowValues): EnergyFlowPaths {
  const solar = Math.max(0, reading.solarProductionW);
  const consumption = Math.max(0, reading.consumptionW);
  const gridImport = Math.max(0, reading.gridImportW);
  const gridExport = Math.max(0, reading.gridExportW);
  const { chargingW: batteryCharge, dischargingW: batteryDischarge } = batteryFlowState(
    reading.batteryPowerW,
  );

  // Charge battery from solar first, then grid import.
  const solarToBattery = Math.min(solar, batteryCharge);
  const gridToBattery = Math.min(Math.max(0, batteryCharge - solarToBattery), gridImport);

  let solarRemaining = Math.max(0, solar - solarToBattery);
  const gridRemaining = Math.max(0, gridImport - gridToBattery);

  // Supply house: solar, then battery discharge, then grid import.
  let solarToHouse = Math.min(solarRemaining, consumption);
  let houseRemaining = Math.max(0, consumption - solarToHouse);

  const batteryToHouse = Math.min(batteryDischarge, houseRemaining);
  houseRemaining = Math.max(0, houseRemaining - batteryToHouse);

  let gridToHouse = Math.min(gridRemaining, houseRemaining);

  // When grid import is active, reserve it for the house before using all solar.
  if (
    gridRemaining > 0 &&
    gridToHouse < gridRemaining &&
    solarRemaining > solarToHouse
  ) {
    solarToHouse = Math.min(
      solarRemaining,
      Math.max(0, consumption - batteryToHouse - gridRemaining),
    );
    houseRemaining = Math.max(0, consumption - solarToHouse - batteryToHouse);
    gridToHouse = Math.min(gridRemaining, houseRemaining);
  }

  solarRemaining = Math.max(0, solarRemaining - solarToHouse);

  // Export: battery discharge to grid first (after house), then solar surplus.
  const batteryToGrid = Math.min(
    Math.max(0, batteryDischarge - batteryToHouse),
    gridExport,
  );
  const exportRemaining = Math.max(0, gridExport - batteryToGrid);
  const solarToGrid = Math.min(solarRemaining, exportRemaining);

  return {
    solarToHouse,
    solarToBattery,
    solarToGrid,
    gridToHouse,
    gridToBattery,
    batteryToHouse,
    batteryToGrid,
  };
}

export function flowIntensity(watts: number, referenceW = 8000): number {
  if (watts < FLOW_THRESHOLD_W) return 0;
  return Math.min(1, watts / referenceW);
}

export function isFlowActive(watts: number): boolean {
  return watts >= FLOW_THRESHOLD_W;
}

export function flowAnimationDuration(watts: number): number {
  const intensity = flowIntensity(watts);
  if (intensity <= 0) return 0;
  // HeartBeat-like pulse travel: ~9s calm, ~4.5s under heavy load.
  const eased = Math.pow(intensity, 0.35);
  return 9 - eased * 4.5;
}

/** Advance dash offset one way along the wire; wraps seamlessly at one pattern period. */
export function advanceFlowDashOffset(
  current: number,
  delta: number,
  period = FLOW_PATH_LENGTH,
): number {
  let next = current - delta;
  while (next <= -period) next += period;
  return next;
}

export type WireAnimationSlot =
  | "solar"
  | "house"
  | "batteryCharge"
  | "batteryDischarge"
  | "gridImport"
  | "gridExport";

export interface WireAnimationSpec {
  pathKey: "solar-inverter" | "inverter-battery" | "house-feed" | "grid-lawn";
  watts: number;
  slot: WireAnimationSlot;
}

export type WireFlowAnchor = "solar" | "inverter" | "battery" | "house" | "gridEnd" | "junction";

/** Physical power direction per animation slot (pulse travels from → to). */
export const WIRE_SLOT_FLOW: Record<
  WireAnimationSlot,
  { pathKey: WireAnimationSpec["pathKey"]; from: WireFlowAnchor; to: WireFlowAnchor }
> = {
  solar: { pathKey: "solar-inverter", from: "solar", to: "inverter" },
  house: { pathKey: "house-feed", from: "inverter", to: "house" },
  batteryCharge: { pathKey: "inverter-battery", from: "inverter", to: "battery" },
  batteryDischarge: { pathKey: "inverter-battery", from: "battery", to: "inverter" },
  gridImport: { pathKey: "grid-lawn", from: "gridEnd", to: "junction" },
  gridExport: { pathKey: "grid-lawn", from: "junction", to: "gridEnd" },
};

/** Physical conduit animations — each cable has a fixed direction; only wattage varies. */
export function computeWireAnimations(values: EnergyFlowValues): WireAnimationSpec[] {
  const wires = computeWireFlows(values);
  const specs: WireAnimationSpec[] = [];

  if (isFlowActive(wires.solarInverterW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.solar.pathKey,
      watts: wires.solarInverterW,
      slot: "solar",
    });
  }

  if (isFlowActive(wires.houseFeedW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.house.pathKey,
      watts: wires.houseFeedW,
      slot: "house",
    });
  }

  if (isFlowActive(wires.batteryChargeW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.batteryCharge.pathKey,
      watts: wires.batteryChargeW,
      slot: "batteryCharge",
    });
  } else if (isFlowActive(wires.batteryDischargeW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.batteryDischarge.pathKey,
      watts: wires.batteryDischargeW,
      slot: "batteryDischarge",
    });
  }

  if (isFlowActive(wires.gridImportW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.gridImport.pathKey,
      watts: wires.gridImportW,
      slot: "gridImport",
    });
  } else if (isFlowActive(wires.gridExportW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.gridExport.pathKey,
      watts: wires.gridExportW,
      slot: "gridExport",
    });
  }

  return specs;
}

export interface StickyWireState {
  batterySlot: "batteryCharge" | "batteryDischarge" | null;
  gridSlot: "gridImport" | "gridExport" | null;
}

export const EMPTY_STICKY_WIRE_STATE: StickyWireState = {
  batterySlot: null,
  gridSlot: null,
};

function resolveBatterySlot(
  batteryPowerW: number,
  prev: StickyWireState["batterySlot"],
): StickyWireState["batterySlot"] {
  if (prev === "batteryCharge") {
    if (batteryPowerW <= -FLOW_SLOT_FLIP_W) return "batteryDischarge";
    if (batteryPowerW >= FLOW_SLOT_EXIT_W) return "batteryCharge";
    if (batteryPowerW > -FLOW_SLOT_EXIT_W) return null;
    return "batteryCharge";
  }
  if (prev === "batteryDischarge") {
    if (batteryPowerW >= FLOW_SLOT_FLIP_W) return "batteryCharge";
    if (batteryPowerW <= -FLOW_SLOT_EXIT_W) return "batteryDischarge";
    if (batteryPowerW < FLOW_SLOT_EXIT_W) return null;
    return "batteryDischarge";
  }
  if (batteryPowerW >= FLOW_THRESHOLD_W) return "batteryCharge";
  if (batteryPowerW <= -FLOW_THRESHOLD_W) return "batteryDischarge";
  return null;
}

function resolveGridSlot(
  gridImportW: number,
  gridExportW: number,
  prev: StickyWireState["gridSlot"],
): StickyWireState["gridSlot"] {
  if (prev === "gridImport") {
    if (gridExportW >= FLOW_SLOT_FLIP_W) return "gridExport";
    if (gridImportW >= FLOW_SLOT_EXIT_W) return "gridImport";
    if (gridExportW < FLOW_SLOT_EXIT_W) return null;
    return "gridImport";
  }
  if (prev === "gridExport") {
    if (gridImportW >= FLOW_SLOT_FLIP_W) return "gridImport";
    if (gridExportW >= FLOW_SLOT_EXIT_W) return "gridExport";
    if (gridImportW < FLOW_SLOT_EXIT_W) return null;
    return "gridExport";
  }
  if (gridImportW >= FLOW_THRESHOLD_W) return "gridImport";
  if (gridExportW >= FLOW_THRESHOLD_W) return "gridExport";
  return null;
}

/** Keep battery/grid animation direction stable between noisy meter updates. */
export function stabilizeWireAnimations(
  values: EnergyFlowValues,
  prev: StickyWireState,
): { specs: WireAnimationSpec[]; next: StickyWireState } {
  const wires = computeWireFlows(values);
  const batterySlot = resolveBatterySlot(values.batteryPowerW, prev.batterySlot);
  const gridSlot = resolveGridSlot(wires.gridImportW, wires.gridExportW, prev.gridSlot);
  const specs: WireAnimationSpec[] = [];

  if (isFlowActive(wires.solarInverterW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.solar.pathKey,
      watts: wires.solarInverterW,
      slot: "solar",
    });
  }

  if (isFlowActive(wires.houseFeedW)) {
    specs.push({
      pathKey: WIRE_SLOT_FLOW.house.pathKey,
      watts: wires.houseFeedW,
      slot: "house",
    });
  }

  if (batterySlot === "batteryCharge") {
    const watts =
      values.batteryPowerW >= FLOW_SLOT_EXIT_W
        ? values.batteryPowerW
        : Math.max(wires.batteryChargeW, Math.abs(values.batteryPowerW));
    if (watts >= FLOW_SLOT_EXIT_W) {
      specs.push({
        pathKey: WIRE_SLOT_FLOW.batteryCharge.pathKey,
        watts,
        slot: "batteryCharge",
      });
    }
  } else if (batterySlot === "batteryDischarge") {
    const watts =
      values.batteryPowerW <= -FLOW_SLOT_EXIT_W
        ? -values.batteryPowerW
        : Math.max(wires.batteryDischargeW, Math.abs(values.batteryPowerW));
    if (watts >= FLOW_SLOT_EXIT_W) {
      specs.push({
        pathKey: WIRE_SLOT_FLOW.batteryDischarge.pathKey,
        watts,
        slot: "batteryDischarge",
      });
    }
  }

  if (gridSlot === "gridImport") {
    const watts = wires.gridImportW;
    if (watts >= FLOW_SLOT_EXIT_W) {
      specs.push({
        pathKey: WIRE_SLOT_FLOW.gridImport.pathKey,
        watts,
        slot: "gridImport",
      });
    }
  } else if (gridSlot === "gridExport") {
    const watts = wires.gridExportW;
    if (watts >= FLOW_SLOT_EXIT_W) {
      specs.push({
        pathKey: WIRE_SLOT_FLOW.gridExport.pathKey,
        watts,
        slot: "gridExport",
      });
    }
  }

  return {
    specs,
    next: { batterySlot, gridSlot },
  };
}

export function readingToFlowValues(reading: Reading): EnergyFlowValues {
  return {
    solarProductionW: reading.solar_production_w,
    consumptionW: reading.consumption_w,
    gridImportW: reading.grid_import_w,
    gridExportW: reading.grid_export_w,
    batteryPowerW: reading.battery_power_w,
    batterySocPct: reading.battery_soc_pct,
  };
}
