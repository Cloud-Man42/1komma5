import type { CSSProperties } from "react";

import type { EvCharger } from "@/lib/api";

const SEGMENT_COUNT = 12;
const ACTIVE_POWER_THRESHOLD_W = 25;

export function getChargerMaxPowerW(charger: EvCharger): number {
  if (charger.max_power_w != null && charger.max_power_w > 0) {
    return charger.max_power_w;
  }

  const current = Math.max(0, charger.max_current_a || 0);
  const voltage = Math.max(0, charger.nominal_voltage_v || 0);
  return charger.phases >= 3 ? current * Math.sqrt(3) * voltage : current * voltage;
}

export function getActivePowerSegments(
  powerW: number | null | undefined,
  maxPowerW: number,
  segmentCount = SEGMENT_COUNT,
): number {
  if (powerW == null || powerW < ACTIVE_POWER_THRESHOLD_W || maxPowerW <= 0 || segmentCount <= 0) {
    return 0;
  }

  return Math.min(segmentCount, Math.ceil((powerW / maxPowerW) * segmentCount));
}

function segmentColor(index: number): string {
  const progress = index / (SEGMENT_COUNT - 1);
  const hue = 212 - progress * 208;
  return `hsl(${hue.toFixed(0)} 82% 62%)`;
}

export function HaloPowerIndicator({ charger }: { charger: EvCharger }) {
  const maxPowerW = getChargerMaxPowerW(charger);
  const powerW = charger.power_w;
  const activeSegments = getActivePowerSegments(powerW, maxPowerW);
  const displayPower = powerW == null ? "—" : `${(Math.max(0, powerW) / 1000).toFixed(1)} kW`;
  const ariaValue = powerW == null ? undefined : Math.min(Math.max(0, powerW), maxPowerW);

  return (
    <div
      className="halo-power-indicator"
      role="meter"
      aria-label="Halo aktuell laddeffekt"
      aria-valuemin={0}
      aria-valuemax={Math.round(maxPowerW)}
      aria-valuenow={ariaValue == null ? undefined : Math.round(ariaValue)}
      aria-valuetext={powerW == null ? "Ingen effektdata" : displayPower}
    >
      <span className="halo-power-value">{displayPower}</span>
      <div className="halo-power-segments" aria-hidden="true">
        {Array.from({ length: SEGMENT_COUNT }, (_, index) => {
          const isActive = index < activeSegments;
          return (
            <span
              key={index}
              className={`halo-power-segment${isActive ? " is-active" : ""}`}
              style={{ "--segment-color": segmentColor(index) } as CSSProperties}
            />
          );
        })}
      </div>
      <span className="halo-power-caption">effekt</span>
    </div>
  );
}
