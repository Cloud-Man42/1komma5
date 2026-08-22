import { FLOW_PATH_LENGTH } from "@/lib/energyFlow";

/** Pause at source before the next pulse (seconds). */
export const LAWN_PULSE_PAUSE_SEC = 0.65;

/** Visible pulse length on normalized path (pathLength=100). */
export const GRID_LAWN_DASH_ON = 12;
/** Gap exceeds the whole cable, so SVG cannot repeat a second dash on the path. */
export const GRID_LAWN_DASH_OFF = FLOW_PATH_LENGTH * 2;
/** Move until the pulse tail has fully left the destination. */
export const GRID_LAWN_TRAVEL = FLOW_PATH_LENGTH + GRID_LAWN_DASH_ON;

export type LawnPulsePhase = "running" | "off";

export interface LawnPulseState {
  progress: number;
  phase: LawnPulsePhase;
  pauseRemaining: number;
}

export interface LawnDashState {
  offset: number;
  phase: LawnPulsePhase;
  pauseRemaining: number;
}

export interface LawnPulseCycleTiming {
  cycleSec: number;
  moveEnd: string;
  jumpEnd: string;
  fadeIn: string;
  fadeOut: string;
}

/** SMIL keyframe timings: move source→dest, hold off at dest, jump to source invisible. */
export function lawnPulseCycleTiming(
  durationSec: number,
  pauseSec = LAWN_PULSE_PAUSE_SEC,
): LawnPulseCycleTiming {
  const cycleSec = durationSec + pauseSec;
  const move = durationSec / cycleSec;
  const fadeIn = (0.04 * move).toFixed(4);
  const fadeOut = (0.94 * move).toFixed(4);
  const moveEnd = move.toFixed(4);
  const jumpEnd = Math.min(1, move + 0.002).toFixed(4);
  return { cycleSec, moveEnd, jumpEnd, fadeIn, fadeOut };
}

export const INITIAL_LAWN_PULSE_STATE: LawnPulseState = {
  progress: 0,
  phase: "running",
  pauseRemaining: 0,
};

export const INITIAL_LAWN_DASH_STATE: LawnDashState = {
  offset: 0,
  phase: "running",
  pauseRemaining: 0,
};

export function lawnPulseTravelProgress(state: LawnPulseState): number {
  if (state.phase === "off") return 1;
  return Math.min(state.progress, 1);
}

export function lawnDashTravelProgress(state: LawnDashState): number {
  if (state.phase === "off") return 1;
  if (GRID_LAWN_TRAVEL <= 0) return 0;
  return Math.max(0, Math.min(1, -state.offset / GRID_LAWN_TRAVEL));
}

export function lawnPulseVisibility(progress: number, phase: LawnPulsePhase): number {
  if (phase === "off") return 0;
  if (progress >= 1) return 0;
  if (progress < 0.02) return progress / 0.02;
  if (progress > 0.97) return 0;
  if (progress > 0.9) return Math.max(0, (0.97 - progress) / 0.07);
  return 1;
}

export function lawnDashVisibility(state: LawnDashState): number {
  return lawnPulseVisibility(lawnDashTravelProgress(state), state.phase);
}

export function advanceLawnPulse(
  state: LawnPulseState,
  deltaSec: number,
  durationSec: number,
  pauseSec = LAWN_PULSE_PAUSE_SEC,
): LawnPulseState {
  if (durationSec <= 0) return state;

  if (state.phase === "off") {
    const pauseRemaining = state.pauseRemaining - deltaSec;
    if (pauseRemaining <= 0) {
      return { progress: 0, phase: "running", pauseRemaining: 0 };
    }
    return { ...state, pauseRemaining };
  }

  const progress = state.progress + deltaSec / durationSec;
  if (progress >= 1) {
    return { progress: 1, phase: "off", pauseRemaining: pauseSec };
  }
  return { ...state, progress };
}

/** One-way dash offset: 0 → -TRAVEL, pause hidden, reset to 0 — never wraps while visible. */
export function advanceLawnDash(
  state: LawnDashState,
  deltaSec: number,
  durationSec: number,
  pauseSec = LAWN_PULSE_PAUSE_SEC,
): LawnDashState {
  if (durationSec <= 0) return state;

  if (state.phase === "off") {
    const pauseRemaining = state.pauseRemaining - deltaSec;
    if (pauseRemaining <= 0) {
      return { offset: 0, phase: "running", pauseRemaining: 0 };
    }
    return { ...state, pauseRemaining };
  }

  const delta = (deltaSec / durationSec) * GRID_LAWN_TRAVEL;
  const offset = state.offset - delta;
  if (offset <= -GRID_LAWN_TRAVEL) {
    return { offset: -GRID_LAWN_TRAVEL, phase: "off", pauseRemaining: pauseSec };
  }
  return { ...state, offset };
}

export function shouldResetLawnPulse(
  prevPath: string,
  prevMode: string,
  nextPath: string,
  nextMode: string,
  active: boolean,
): boolean {
  if (!active) return true;
  return prevPath !== nextPath || prevMode !== nextMode;
}
