"use client";

import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SpaHistory, SpaStatus } from "@/lib/api";
import { breakdownShares } from "./spaDashboardHelpers";

function formatHour(iso: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
}

export function SpaConsumption24hChart({
  history,
  status,
}: {
  history: SpaHistory | null;
  status: SpaStatus;
}) {
  const [mode, setMode] = useState<"kw" | "kwh">("kw");
  const shares = breakdownShares(status);

  const chartData = useMemo(() => {
    const points = history?.points ?? [];
    return points.map((point) => {
      const power = point.power_w ?? 0;
      const energy = point.energy_kwh ?? 0;
      const base = mode === "kw" ? power / 1000 : energy;
      return {
        time: formatHour(point.timestamp),
        heater: Math.round(base * shares.heater * 100) / 100,
        pumps: Math.round(base * shares.pumps * 100) / 100,
        circulation: Math.round(base * shares.circulation * 100) / 100,
        blower: Math.round(base * shares.blower * 100) / 100,
        total: Math.round(base * 100) / 100,
      };
    });
  }, [history, mode, shares]);

  const yMax = useMemo(() => {
    let max = 0;
    for (const row of chartData) max = Math.max(max, row.total);
    return Math.max(1, Math.ceil(max * 1.15));
  }, [chartData]);

  return (
    <section className="sdash-panel sdash-consumption-panel">
      <div className="sdash-panel-head">
        <h2 className="sdash-panel-title">FÖRBRUKNING – SENASTE 24 TIMMARNA</h2>
        <div className="sdash-toggle" role="group" aria-label="Enhet">
          <button
            type="button"
            className={mode === "kw" ? "is-active" : ""}
            onClick={() => setMode("kw")}
          >
            kW
          </button>
          <button
            type="button"
            className={mode === "kwh" ? "is-active" : ""}
            onClick={() => setMode("kwh")}
          >
            kWh
          </button>
        </div>
      </div>
      {chartData.length === 0 ? (
        <p className="sdash-muted">Väntar på mätdata.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="4 4" />
            <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              domain={[0, yMax]}
              label={{
                value: mode === "kw" ? "kW" : "kWh",
                angle: -90,
                position: "insideLeft",
                fill: "#64748b",
              }}
            />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
            <Area type="monotone" dataKey="heater" stackId="a" stroke="#f87171" fill="#f87171" fillOpacity={0.55} name="Värmare" />
            <Area type="monotone" dataKey="pumps" stackId="a" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.55} name="Pumpar" />
            <Area type="monotone" dataKey="circulation" stackId="a" stroke="#4ade80" fill="#4ade80" fillOpacity={0.55} name="Cirkulation" />
            <Area type="monotone" dataKey="blower" stackId="a" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.55} name="Blower" />
            <Line type="monotone" dataKey="total" stroke="#e2e8f0" strokeWidth={1.5} dot={false} name="Totalt" />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
