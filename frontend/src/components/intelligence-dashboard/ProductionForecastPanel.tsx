"use client";

import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Reading, SolarForecast } from "@/lib/api";
import {
  buildProductionChartData,
  chartYMax,
  formatChartClock,
  hasForecastSeries,
} from "./productionChartData";

function kwh(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`;
}

export function ProductionForecastPanel({
  readings,
  forecast,
  timezone = "Europe/Stockholm",
}: {
  readings: Reading[];
  forecast: SolarForecast | null;
  timezone?: string;
}) {
  const nowIso = new Date().toISOString();
  const nowLabel = formatChartClock(nowIso, timezone);

  const chartData = useMemo(
    () => buildProductionChartData({ readings, forecast, timezone, now: nowIso }),
    [readings, forecast, timezone, nowIso],
  );

  const yMax = useMemo(() => chartYMax(chartData), [chartData]);
  const showForecast = hasForecastSeries(chartData);

  const deviationKwh =
    forecast && forecast.forecast_so_far_kwh > 0
      ? forecast.actual_today_kwh - forecast.forecast_so_far_kwh
      : null;
  const deviationPct =
    deviationKwh != null && forecast && forecast.forecast_so_far_kwh > 0
      ? (deviationKwh / forecast.forecast_so_far_kwh) * 100
      : null;

  return (
    <section className="idash-panel idash-production-panel">
      <h2 className="idash-panel-title">PRODUKTION: PROGNOS vs VERKLIGHET</h2>
      <div className="idash-production-body">
        <div className="idash-production-chart">
          {chartData.length === 0 ? (
            <p className="idash-muted">Ingen produktionsdata ännu.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(148,163,184,0.1)" strokeDasharray="4 4" />
                <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  domain={[0, yMax]}
                  label={{ value: "kW", angle: -90, position: "insideLeft", fill: "#64748b" }}
                />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}
                  labelStyle={{ color: "#e2e8f0" }}
                  formatter={(value: number, name: string) => [
                    `${value.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} kW`,
                    name,
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
                  formatter={(value) => <span style={{ color: "#94a3b8" }}>{value}</span>}
                />
                <Area
                  type="monotone"
                  dataKey="actualKw"
                  name="Verklig"
                  stroke="#22d3ee"
                  fill="url(#idashActualFill)"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
                {showForecast ? (
                  <Line
                    type="monotone"
                    dataKey="forecastKw"
                    name="Prognos"
                    stroke="#fbbf24"
                    strokeDasharray="6 4"
                    strokeWidth={2.5}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ) : null}
                <ReferenceLine x={nowLabel} stroke="#94a3b8" strokeDasharray="4 4" label="Nu" />
                <defs>
                  <linearGradient id="idashActualFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
              </ComposedChart>
            </ResponsiveContainer>
          )}
          {chartData.length > 0 && !showForecast ? (
            <p className="idash-muted idash-production-chart-hint">Prognoslinje saknas — kontrollera solprognos.</p>
          ) : null}
        </div>
        <dl className="idash-production-stats">
          <div>
            <dt>Förväntad idag</dt>
            <dd>{forecast ? kwh(forecast.expected_today_kwh) : "—"}</dd>
          </div>
          <div>
            <dt>Intervall</dt>
            <dd>
              {forecast
                ? `${kwh(forecast.lower_today_kwh)} – ${kwh(forecast.upper_today_kwh)}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt>Producerat hittills</dt>
            <dd>{forecast ? kwh(forecast.actual_today_kwh) : "—"}</dd>
          </div>
          <div>
            <dt>Förväntat vid denna tid</dt>
            <dd>{forecast ? kwh(forecast.forecast_so_far_kwh) : "—"}</dd>
          </div>
          <div>
            <dt>Avvikelse</dt>
            <dd className={deviationKwh != null && deviationKwh < 0 ? "idash-negative" : ""}>
              {deviationKwh != null && deviationPct != null
                ? `${deviationKwh.toLocaleString("sv-SE", { maximumFractionDigits: 1, signDisplay: "exceptZero" })} kWh (${deviationPct.toFixed(1).replace(".", ",")} %)`
                : "—"}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
