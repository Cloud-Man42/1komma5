"use client";

import { memo, useEffect, useMemo, useRef, type CSSProperties } from "react";
import {
  flowAnimationDuration,
  flowIntensity,
  isFlowActive,
} from "@/lib/energyFlow";
import { ENERGY_FLOW_PALETTE } from "@/lib/energyFlowColors";
import { directionMarkersForPath } from "@/lib/energyFlowSceneLayout";
import {
  advanceLawnPulse,
  INITIAL_LAWN_PULSE_STATE,
  lawnPulseVisibility,
  shouldResetLawnPulse,
  type LawnPulseState,
} from "@/lib/gridLawnFlow";

interface GridLawnFlowPulseProps {
  /** Oriented path: import = meter → house, export = house → meter. */
  path: string;
  watts: number;
  mode: "import" | "export";
  glowFilterId?: string;
}

/**
 * Fixed arrows light in sequence from path start → path end.
 * No element changes position, so the cable dogleg cannot look like a bounce.
 * Import path is oriented meter→house (red); export is house→meter (green).
 */
export const GridLawnFlowPulse = memo(function GridLawnFlowPulse({
  path,
  watts,
  mode,
  glowFilterId,
}: GridLawnFlowPulseProps) {
  const active = isFlowActive(watts);
  const palette = mode === "export" ? ENERGY_FLOW_PALETTE.green : ENERGY_FLOW_PALETTE.red;
  const intensity = flowIntensity(watts);
  const durationSec = flowAnimationDuration(watts);

  const markers = useMemo(() => directionMarkersForPath(path, 8), [path]);
  const markerRefs = useRef<Array<SVGGElement | null>>([]);
  const stateRef = useRef<LawnPulseState>(INITIAL_LAWN_PULSE_STATE);
  const sessionRef = useRef({ path: "", mode: "" });
  const durationRef = useRef(durationSec);
  const intensityRef = useRef(intensity);

  durationRef.current = durationSec;
  intensityRef.current = intensity;

  useEffect(() => {
    if (shouldResetLawnPulse(sessionRef.current.path, sessionRef.current.mode, path, mode, active)) {
      stateRef.current = INITIAL_LAWN_PULSE_STATE;
    }
    sessionRef.current = { path, mode };

    const markerElements = markerRefs.current.slice(0, markers.length);
    if (markerElements.length === 0) return;

    if (!active || durationRef.current <= 0) {
      markerElements.forEach((element) => element?.setAttribute("visibility", "hidden"));
      return;
    }

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const applyFrame = () => {
      const state = stateRef.current;
      const cycleVisibility = lawnPulseVisibility(state.progress, state.phase);
      markerElements.forEach((element, index) => {
        if (!element) return;
        const distance = Math.abs(markers[index].progress - state.progress);
        const wave = Math.max(0, 1 - distance / 0.24);
        const baseline = 0.42 + intensityRef.current * 0.12;
        const opacity = baseline + cycleVisibility * wave * (1 - baseline);
        element.setAttribute("visibility", "visible");
        element.setAttribute("opacity", String(opacity));
      });
    };

    if (prefersReducedMotion) {
      markerElements.forEach((element) => {
        element?.setAttribute("visibility", "visible");
        element?.setAttribute("opacity", "0.55");
      });
      return;
    }

    let frame = 0;
    let last = performance.now();

    applyFrame();
    const tick = (now: number) => {
      const deltaSec = Math.min(0.05, (now - last) / 1000);
      last = now;
      stateRef.current = advanceLawnPulse(stateRef.current, deltaSec, durationRef.current);
      applyFrame();
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, path, mode, markers]);

  if (!active || durationSec <= 0) return null;

  const trackWidth = 0.16 + intensity * 0.08;

  return (
    <g
      className={`energy-grid-lawn-flow energy-grid-lawn-flow-${mode}`}
      style={
        {
          "--flow-glow": palette.glow,
          "--flow-core": palette.core,
          "--flow-intensity": intensity,
        } as CSSProperties
      }
    >
      <path
        d={path}
        fill="none"
        className="energy-grid-lawn-flow-track"
        stroke={palette.glow}
        strokeWidth={trackWidth}
      />
      <g className="energy-grid-lawn-flow-direction">
        {markers.map((marker, index) => (
          <g
            key={`${marker.progress}-${index}`}
            ref={(element) => {
              markerRefs.current[index] = element;
            }}
            className="energy-grid-lawn-flow-arrow"
            transform={`translate(${marker.x} ${marker.y}) rotate(${marker.angleDeg})`}
            visibility="hidden"
          >
            <path
              d="M -1.38 -0.92 L 1.38 0 L -1.38 0.92 L -0.56 0 Z"
              className="energy-grid-lawn-flow-arrow-glow"
              fill={palette.glow}
              stroke={palette.glow}
              strokeWidth={0.16}
              filter={glowFilterId ? `url(#${glowFilterId})` : undefined}
            />
            <path
              d="M -0.86 -0.5 L 0.86 0 L -0.86 0.5 L -0.34 0 Z"
              className="energy-grid-lawn-flow-arrow-core"
              fill={palette.core}
              stroke={palette.core}
              strokeWidth={0.1}
            />
          </g>
        ))}
      </g>
    </g>
  );
}, lawnPulsePropsEqual);

function lawnPulsePropsEqual(prev: GridLawnFlowPulseProps, next: GridLawnFlowPulseProps): boolean {
  if (prev.path !== next.path || prev.mode !== next.mode || prev.glowFilterId !== next.glowFilterId) {
    return false;
  }
  const prevActive = isFlowActive(prev.watts);
  const nextActive = isFlowActive(next.watts);
  if (prevActive !== nextActive) return false;
  if (!nextActive) return true;
  return (
    Math.round(flowAnimationDuration(prev.watts)) ===
    Math.round(flowAnimationDuration(next.watts))
  );
}
