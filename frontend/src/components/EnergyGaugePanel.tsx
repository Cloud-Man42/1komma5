"use client";

import { useMemo } from "react";

import { AnalogBoostGauge } from "@/components/AnalogBoostGauge";
import type { DashboardSolarSection, DashboardTodaySection } from "@/lib/api";
import type { Reading } from "@/lib/api";
import { formatWatts } from "@/lib/api";
import {
  batteryFlowState,
  computeEnergyFlows,
  computeWireFlows,
  isFlowActive,
  readingToFlowValues,
  normalizeFlowValues,
} from "@/lib/energyFlow";
import { resolveGaugeScales } from "@/lib/analogGauge";

interface EnergyGaugePanelProps {
  reading: Reading;
  compact?: boolean;
  evPowerW?: number;
  solar?: DashboardSolarSection | null;
  today?: DashboardTodaySection | null;
  mainFuseA?: number | null;
}

function formatKwh(value: number | null | undefined): string | undefined {
  if (value == null || Number.isNaN(value)) return undefined;
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh idag`;
}

export function EnergyGaugePanel({
  reading,
  compact = false,
  evPowerW = 0,
  solar = null,
  today = null,
  mainFuseA = null,
}: EnergyGaugePanelProps) {
  const values = useMemo(() => normalizeFlowValues(readingToFlowValues(reading)), [reading]);
  const wires = useMemo(() => computeWireFlows(values), [values]);
  const flows = useMemo(() => computeEnergyFlows(values), [values]);
  const battery = batteryFlowState(values.batteryPowerW);
  const soc = Math.min(100, Math.max(0, values.batterySocPct));

  const gridSignedW =
    wires.gridImportW >= 25
      ? wires.gridImportW
      : wires.gridExportW >= 25
        ? -wires.gridExportW
        : 0;

  const scales = useMemo(
    () =>
      resolveGaugeScales({
        solarW: wires.solarInverterW,
        houseW: wires.houseFeedW,
        batteryW: values.batteryPowerW,
        gridW: gridSignedW,
        solarPeakW: solar?.peak_power_w,
        inverterMaxKw: solar?.inverter_max_power_kw,
        mainFuseA,
      }),
    [
      wires.solarInverterW,
      wires.houseFeedW,
      values.batteryPowerW,
      gridSignedW,
      solar?.peak_power_w,
      solar?.inverter_max_power_kw,
      mainFuseA,
    ],
  );

  const gridDirection =
    wires.gridImportW >= 25
      ? "Import från nät"
      : wires.gridExportW >= 25
        ? "Export till nät"
        : "Vila";

  const batteryDirection =
    battery.mode === "charging"
      ? "Laddning"
      : battery.mode === "discharging"
        ? "Urladdning"
        : "Vila";

  const houseSecondary =
    evPowerW >= 25 ? `Varav laddbox ${formatWatts(evPowerW)}` : undefined;

  const solarSecondary =
    formatKwh(today?.produced_kwh) ??
    (solar?.expected_today_kwh != null
      ? `Prognos ${solar.expected_today_kwh.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`
      : undefined);

  const flowNotes = [
    { label: "Sol → hus", watts: flows.solarToHouse },
    { label: "Sol → batteri", watts: flows.solarToBattery },
    { label: "Sol → nät", watts: flows.solarToGrid },
    { label: "Nät → hus", watts: flows.gridToHouse },
    { label: "Batteri → hus", watts: flows.batteryToHouse },
  ].filter((item) => isFlowActive(item.watts));

  return (
    <div
      className={`energy-gauge-panel ${compact ? "energy-gauge-panel-compact" : ""}`}
      aria-label="Energimätare live"
    >
      <div className="energy-gauge-grid">
        <AnalogBoostGauge
          compact={compact}
          label="Solenergi"
          icon="☀"
          watts={wires.solarInverterW}
          maxW={scales.solarMaxW}
          accent="#f59e0b"
          accentGlow="#fcd34d"
          directionLabel={wires.solarInverterW >= 25 ? "Produktion" : "Vila"}
          secondary={solarSecondary}
        />
        <AnalogBoostGauge
          compact={compact}
          label="Hushåll"
          icon="⌂"
          watts={wires.houseFeedW}
          maxW={scales.houseMaxW}
          accent="#38bdf8"
          accentGlow="#7dd3fc"
          directionLabel="Förbrukning"
          secondary={houseSecondary}
        />
        <AnalogBoostGauge
          compact={compact}
          label="Batteri"
          icon="🔋"
          watts={values.batteryPowerW}
          maxW={scales.batteryMaxW}
          mode="bidirectional"
          accent={
            battery.mode === "discharging"
              ? "#fb7185"
              : battery.mode === "charging"
                ? "#34d399"
                : "#94a3b8"
          }
          accentGlow={
            battery.mode === "discharging"
              ? "#fda4af"
              : battery.mode === "charging"
                ? "#6ee7b7"
                : "#cbd5e1"
          }
          directionLabel={batteryDirection}
          secondary={`${soc.toFixed(0)} % SOC`}
        />
        <AnalogBoostGauge
          compact={compact}
          label="Nät"
          icon="⚡"
          watts={gridSignedW}
          maxW={scales.gridMaxW}
          mode="bidirectional"
          accent={gridSignedW < 0 ? "#4ade80" : gridSignedW > 0 ? "#f87171" : "#94a3b8"}
          accentGlow={gridSignedW < 0 ? "#86efac" : gridSignedW > 0 ? "#fca5a5" : "#cbd5e1"}
          directionLabel={gridDirection}
        />
      </div>

      {!compact && flowNotes.length > 0 && (
        <ul className="energy-gauge-flow-notes" aria-label="Aktiva energiflöden">
          {flowNotes.map((item) => (
            <li key={item.label}>
              <span>{item.label}</span>
              <strong>{formatWatts(item.watts)}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
