"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SpaHistory } from "@/lib/api";

function formatHour(iso: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
}

export function SpaTodayHistoryChart({ history }: { history: SpaHistory | null }) {
  const chartData = useMemo(
    () =>
      (history?.points ?? []).map((point) => ({
        time: point.period_label ?? formatHour(point.timestamp),
        kwh: Math.round((point.energy_kwh ?? 0) * 100) / 100,
      })),
    [history],
  );

  const yMax = useMemo(() => {
    let max = 0;
    for (const row of chartData) max = Math.max(max, row.kwh);
    return Math.max(1, Math.ceil(max * 1.15 * 10) / 10);
  }, [chartData]);

  return (
    <section className="sdash-panel sdash-history-panel">
      <h2 className="sdash-panel-title">HISTORIK – DAGENS FÖRBRUKNING</h2>
      {chartData.length === 0 ? (
        <p className="sdash-muted">Väntar på mätdata.</p>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="sdashBarFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              domain={[0, yMax]}
              label={{ value: "kWh", angle: -90, position: "insideLeft", fill: "#64748b" }}
            />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Bar dataKey="kwh" fill="url(#sdashBarFill)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
