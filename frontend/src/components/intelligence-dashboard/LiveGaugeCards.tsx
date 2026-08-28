"use client";

import { AnalogBoostGauge } from "@/components/AnalogBoostGauge";
import type { DashboardLiveSection, DashboardSolarSection, Reading } from "@/lib/api";
import { formatWatts } from "@/lib/api";
import { resolveGaugeScales } from "@/lib/analogGauge";
import {
  batteryFlowState,
  computeWireFlows,
  normalizeFlowValues,
  readingToFlowValues,
} from "@/lib/energyFlow";
import { Sparkline } from "./Sparkline";

function SocBar({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div className="idash-soc-bar" aria-hidden="true">
      <div className="idash-soc-bar-fill" style={{ width: `${clamped}%` }} />
    </div>
  );
}

export function LiveGaugeCards({
  reading,
  live,
  solar,
  sparkSolar,
  sparkHouse,
  sparkGrid,
}: {
  reading: Reading;
  live: DashboardLiveSection | null;
  solar?: DashboardSolarSection | null;
  sparkSolar: number[];
  sparkHouse: number[];
  sparkGrid: number[];
}) {
  const values = normalizeFlowValues(readingToFlowValues(reading));
  const wires = computeWireFlows(values);
  const battery = batteryFlowState(values.batteryPowerW);
  const soc = Math.min(100, Math.max(0, values.batterySocPct));

  const gridSignedW =
    wires.gridImportW >= 25
      ? wires.gridImportW
      : wires.gridExportW >= 25
        ? -wires.gridExportW
        : 0;

  const scales = resolveGaugeScales({
    solarW: wires.solarInverterW,
    houseW: wires.houseFeedW,
    batteryW: values.batteryPowerW,
    gridW: gridSignedW,
    solarPeakW: solar?.peak_power_w,
    inverterMaxKw: solar?.inverter_max_power_kw,
  });

  const cards = [
    {
      key: "production",
      title: "PRODUKTION",
      accent: "#fbbf24",
      glow: "#fcd34d",
      watts: wires.solarInverterW,
      maxW: scales.solarMaxW,
      subtitle: "Solenergi just nu",
      inset: `+ ${formatWatts(wires.solarInverterW)}`,
      spark: sparkSolar,
      footer: <Sparkline values={sparkSolar} color="#fbbf24" />,
    },
    {
      key: "consumption",
      title: "FÖRBRUKNING",
      accent: "#38bdf8",
      glow: "#7dd3fc",
      watts: wires.houseFeedW,
      maxW: scales.houseMaxW,
      subtitle: "Hushåll just nu",
      inset: live?.consumption_w != null ? `+ ${formatWatts(live.consumption_w)}` : undefined,
      spark: sparkHouse,
      footer: <Sparkline values={sparkHouse} color="#38bdf8" />,
    },
    {
      key: "battery",
      title: "BATTERI",
      accent: "#a78bfa",
      glow: "#c4b5fd",
      watts: values.batteryPowerW,
      maxW: scales.batteryMaxW,
      mode: "bidirectional" as const,
      subtitle:
        battery.mode === "discharging"
          ? "Urladdning"
          : battery.mode === "charging"
            ? "Laddning"
            : "Vila",
      inset: `${soc.toFixed(0)}% SOC`,
      footer: <SocBar pct={soc} />,
    },
    {
      key: "grid",
      title: "EXPORT TILL NÄT",
      accent: "#4ade80",
      glow: "#86efac",
      watts: gridSignedW,
      maxW: scales.gridMaxW,
      mode: "bidirectional" as const,
      subtitle: "Näteffekt just nu",
      inset: gridSignedW < 0 ? `↑ ${formatWatts(Math.abs(gridSignedW))}` : formatWatts(Math.abs(gridSignedW)),
      spark: sparkGrid,
      footer: <Sparkline values={sparkGrid} color="#4ade80" />,
    },
  ];

  return (
    <div className="idash-gauge-row">
      {cards.map((card) => (
        <article key={card.key} className={`idash-gauge-card idash-gauge-card-${card.key}`}>
          <p className="idash-card-kicker">{card.title}</p>
          <div className="idash-gauge-card-body">
            <AnalogBoostGauge
              compact
              label=""
              icon=""
              watts={card.watts}
              maxW={card.maxW}
              mode={card.mode}
              accent={card.accent}
              accentGlow={card.glow}
            />
            <div className="idash-gauge-meta">
              {card.inset ? <span className="idash-gauge-inset">{card.inset}</span> : null}
              <p className="idash-gauge-sub">{card.subtitle}</p>
            </div>
          </div>
          <div className="idash-gauge-footer">{card.footer}</div>
        </article>
      ))}
    </div>
  );
}
