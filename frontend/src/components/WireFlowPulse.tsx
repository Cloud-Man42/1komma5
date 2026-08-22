"use client";



import { useEffect, useRef, type CSSProperties } from "react";

import type { EnergyFlowKind } from "@/lib/energyFlowColors";

import { paletteForFlowKind } from "@/lib/energyFlowColors";

import {

  advanceFlowDashOffset,

  FLOW_DASH_OFF,

  FLOW_DASH_ON,

  FLOW_PATH_LENGTH,

  flowAnimationDuration,

  flowIntensity,

  isFlowActive,

} from "@/lib/energyFlow";



const PULSE_BANDS = 3;



interface WireFlowPulseProps {

  path: string;

  watts: number;

  kind: EnergyFlowKind;

}



/** HeartBeat-style flow: dash segments scroll one way along the wire — never reverse. */

export function WireFlowPulse({ path, watts, kind }: WireFlowPulseProps) {

  const active = isFlowActive(watts);

  const palette = paletteForFlowKind(kind);

  const intensity = flowIntensity(watts);

  const durationSec = flowAnimationDuration(watts);

  const trackRef = useRef<SVGPathElement>(null);

  const glowRefs = useRef<(SVGPathElement | null)[]>([]);

  const coreRefs = useRef<(SVGPathElement | null)[]>([]);

  const offsetsRef = useRef(

    Array.from({ length: PULSE_BANDS }, (_, band) => -(band / PULSE_BANDS) * FLOW_PATH_LENGTH),

  );



  useEffect(() => {

    if (!active || durationSec <= 0) {

      for (let band = 0; band < PULSE_BANDS; band += 1) {

        glowRefs.current[band]?.setAttribute("visibility", "hidden");

        coreRefs.current[band]?.setAttribute("visibility", "hidden");

      }

      return;

    }



    const prefersReducedMotion =

      typeof window !== "undefined" &&

      typeof window.matchMedia === "function" &&

      window.matchMedia("(prefers-reduced-motion: reduce)").matches;



    if (prefersReducedMotion) {

      for (let band = 0; band < PULSE_BANDS; band += 1) {

        glowRefs.current[band]?.setAttribute("stroke-dashoffset", "0");

        coreRefs.current[band]?.setAttribute("stroke-dashoffset", "0");

        glowRefs.current[band]?.setAttribute("visibility", band === 0 ? "visible" : "hidden");

        coreRefs.current[band]?.setAttribute("visibility", band === 0 ? "visible" : "hidden");

      }

      return;

    }



    let frame = 0;

    let last = performance.now();

    const glowWidth = 0.28 + intensity * 0.16;

    const coreWidth = 0.14 + intensity * 0.1;

    const dashPattern = `${FLOW_DASH_ON} ${FLOW_DASH_OFF}`;

    const coreDashOn = Math.max(4, FLOW_DASH_ON * 0.55);

    const coreDashPattern = `${coreDashOn} ${FLOW_PATH_LENGTH - coreDashOn}`;



    const applyBand = (band: number) => {

      const glow = glowRefs.current[band];

      const core = coreRefs.current[band];

      if (!glow || !core) return;

      const offset = String(offsetsRef.current[band]);

      glow.setAttribute("stroke-dasharray", dashPattern);

      glow.setAttribute("stroke-dashoffset", offset);

      glow.setAttribute("stroke-width", String(glowWidth));

      glow.setAttribute("visibility", "visible");

      core.setAttribute("stroke-dasharray", coreDashPattern);

      core.setAttribute("stroke-dashoffset", offset);

      core.setAttribute("stroke-width", String(coreWidth));

      core.setAttribute("visibility", "visible");

    };



    const tick = (now: number) => {

      const deltaSec = Math.min(0.05, (now - last) / 1000);

      last = now;

      const delta = (deltaSec / durationSec) * FLOW_PATH_LENGTH;

      for (let band = 0; band < PULSE_BANDS; band += 1) {

        offsetsRef.current[band] = advanceFlowDashOffset(offsetsRef.current[band], delta);

        applyBand(band);

      }

      frame = requestAnimationFrame(tick);

    };



    for (let band = 0; band < PULSE_BANDS; band += 1) {

      applyBand(band);

    }

    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);

  }, [active, durationSec, intensity, path]);



  if (!active) return null;



  const trackWidth = 0.18 + intensity * 0.1;



  return (

    <g

      className="energy-wire-flow"

      style={

        {

          "--flow-glow": palette.glow,

          "--flow-core": palette.core,

          "--flow-intensity": intensity,

        } as CSSProperties

      }

    >

      <path

        ref={trackRef}

        d={path}

        pathLength={FLOW_PATH_LENGTH}

        fill="none"

        className="energy-wire-flow-track"

        stroke={palette.glow}

        strokeWidth={trackWidth}

      />

      {Array.from({ length: PULSE_BANDS }, (_, band) => (

        <g key={band}>

          <path

            ref={(node) => {

              glowRefs.current[band] = node;

            }}

            d={path}

            pathLength={FLOW_PATH_LENGTH}

            fill="none"

            className="energy-wire-flow-glow"

            stroke={palette.glow}

            visibility="hidden"

          />

          <path

            ref={(node) => {

              coreRefs.current[band] = node;

            }}

            d={path}

            pathLength={FLOW_PATH_LENGTH}

            fill="none"

            className="energy-wire-flow-core"

            stroke={palette.core}

            visibility="hidden"

          />

        </g>

      ))}

    </g>

  );

}


