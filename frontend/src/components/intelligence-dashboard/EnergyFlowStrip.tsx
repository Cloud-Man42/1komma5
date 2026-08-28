"use client";

import type { Reading } from "@/lib/api";
import { formatWatts } from "@/lib/api";
import {
  batteryFlowState,
  computeEnergyFlows,
  computeWireFlows,
  isFlowActive,
  normalizeFlowValues,
  readingToFlowValues,
} from "@/lib/energyFlow";

function FlowNode({
  label,
  icon,
  value,
  sub,
  tone,
}: {
  label: string;
  icon: string;
  value: string;
  sub?: string;
  tone: "solar" | "house" | "battery" | "grid";
}) {
  return (
    <div className={`idash-flow-node idash-flow-node-${tone}`}>
      <span className="idash-flow-node-icon" aria-hidden="true">
        {icon}
      </span>
      <strong>{label}</strong>
      <span className="idash-flow-node-value">{value}</span>
      {sub ? <span className="idash-flow-node-sub">{sub}</span> : null}
    </div>
  );
}

function FlowLine({ active, tone }: { active: boolean; tone: string }) {
  return (
    <div className={`idash-flow-line ${active ? "idash-flow-line-active" : ""}`} data-tone={tone}>
      <span className="idash-flow-line-glow" />
    </div>
  );
}

export function EnergyFlowStrip({ reading }: { reading: Reading }) {
  const values = normalizeFlowValues(readingToFlowValues(reading));
  const wires = computeWireFlows(values);
  const flows = computeEnergyFlows(values);
  const battery = batteryFlowState(values.batteryPowerW);
  const soc = Math.min(100, Math.max(0, values.batterySocPct));

  const gridExport = wires.gridExportW >= 25;
  const gridImport = wires.gridImportW >= 25;

  return (
    <section className="idash-panel idash-flow-panel">
      <h2 className="idash-panel-title">ENERGIFLÖDE</h2>
      <div className="idash-flow-strip">
        <FlowNode
          tone="solar"
          label="Sol"
          icon="☀"
          value={formatWatts(wires.solarInverterW)}
        />
        <FlowLine active={isFlowActive(flows.solarToHouse)} tone="solar" />
        <FlowNode
          tone="house"
          label="Hus"
          icon="⌂"
          value={formatWatts(wires.houseFeedW)}
        />
        <FlowLine
          active={isFlowActive(flows.batteryToHouse) || isFlowActive(flows.solarToBattery)}
          tone="battery"
        />
        <FlowNode
          tone="battery"
          label="Batteri"
          icon="🔋"
          value={formatWatts(Math.abs(values.batteryPowerW))}
          sub={`${soc.toFixed(0)}% SOC · ${
            battery.mode === "discharging" ? "Urladdning" : battery.mode === "charging" ? "Laddning" : "Vila"
          }`}
        />
        <FlowLine active={gridExport || gridImport} tone="grid" />
        <FlowNode
          tone="grid"
          label="Nät"
          icon="⚡"
          value={formatWatts(gridExport ? wires.gridExportW : wires.gridImportW)}
          sub={gridExport ? "Export" : gridImport ? "Import" : "Vila"}
        />
      </div>
    </section>
  );
}
