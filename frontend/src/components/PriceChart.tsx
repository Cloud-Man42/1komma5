"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MarketPricesResponse } from "@/lib/api";
import { formatOrePerKwh, toOrePerKwh } from "@/lib/prices";

interface PriceChartProps {
  prices: MarketPricesResponse | null;
}

function useIsMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [breakpoint]);

  return isMobile;
}

function formatHour(timestamp: string, timezone: string, isMobile: boolean) {
  return new Date(timestamp).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: isMobile ? undefined : "2-digit",
    timeZone: timezone,
  });
}

function formatPrice(valuePerKwh: number) {
  return formatOrePerKwh(valuePerKwh);
}

function priceColor(value: number, average: number) {
  if (value >= average * 1.15) return "#ef4444";
  if (value <= average * 0.85) return "#22c55e";
  return "#38bdf8";
}

export function PriceChart({ prices }: PriceChartProps) {
  const isMobile = useIsMobile();

  const chart = useMemo(() => {
    if (!prices || prices.points.length === 0) return null;

    const average =
      prices.average_all_in_eur_kwh ??
      prices.points.reduce((sum, point) => sum + (point.all_in_eur_kwh ?? point.spot_eur_kwh), 0) /
        prices.points.length;

    const now = Date.now();
    const data = prices.points.map((point) => {
      const value = point.all_in_eur_kwh ?? point.spot_eur_kwh;
      return {
        time: formatHour(point.timestamp, prices.timezone, isMobile),
        timestamp: point.timestamp,
        allIn: toOrePerKwh(value),
        spot: toOrePerKwh(point.spot_eur_kwh),
        isCurrent: Math.abs(new Date(point.timestamp).getTime() - now) < 45 * 60 * 1000,
      };
    });

    const currentIndex = data.findIndex((point) => point.isCurrent);
    const averageOre = toOrePerKwh(average);

    return { data, average: averageOre, currentIndex };
  }, [prices, isMobile]);

  if (!prices) {
    return <p className="muted">Laddar elpriser…</p>;
  }

  if (!chart) {
    return <p className="muted">Inga elpriser tillgängliga från Heartbeat.</p>;
  }

  const chartHeight = isMobile ? 260 : 320;
  const tickStyle = { fill: "#94a3b8", fontSize: isMobile ? 10 : 12 };
  const labelStyle = { color: "#e2e8f0", fontSize: isMobile ? 12 : 14 };

  return (
    <section className="price-chart-section">
      <div className="price-chart-header">
        <div>
          <h3 className="section-title">Elpris 24 timmar</h3>
          <p className="muted">Timpriser från Heartbeat i öre/kWh inkl. nät och moms där tillgängligt.</p>
        </div>
        <dl className="price-summary">
          <div>
            <dt>Nu</dt>
            <dd>
              {prices.current_price_eur_kwh != null
                ? formatPrice(prices.current_price_eur_kwh)
                : "–"}
            </dd>
          </div>
          <div>
            <dt>Lägst</dt>
            <dd>
              {prices.lowest_all_in_eur_kwh != null
                ? formatPrice(prices.lowest_all_in_eur_kwh)
                : "–"}
            </dd>
          </div>
          <div>
            <dt>Högst</dt>
            <dd>
              {prices.highest_all_in_eur_kwh != null
                ? formatPrice(prices.highest_all_in_eur_kwh)
                : "–"}
            </dd>
          </div>
        </dl>
      </div>
      <div className="chart">
        <div className="chart-inner">
          <ResponsiveContainer width="100%" height={chartHeight}>
            <ComposedChart
              data={chart.data}
              margin={
                isMobile
                  ? { top: 8, right: 4, left: -12, bottom: 4 }
                  : { top: 8, right: 16, left: 0, bottom: 8 }
              }
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="time"
                tick={tickStyle}
                interval={isMobile ? "preserveStartEnd" : 1}
                angle={isMobile ? -35 : 0}
                textAnchor={isMobile ? "end" : "middle"}
                height={isMobile ? 50 : 30}
              />
              <YAxis
                tick={tickStyle}
                width={isMobile ? 48 : 58}
                tickFormatter={(value) => `${Math.round(value)}`}
                label={{
                  value: "öre/kWh",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#94a3b8",
                  fontSize: isMobile ? 10 : 11,
                }}
              />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155" }}
                labelStyle={labelStyle}
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)} öre/kWh`,
                  name === "allIn" ? "All-in" : "Spot",
                ]}
              />
              <ReferenceLine
                y={chart.average}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                label={{
                  value: "Snitt",
                  fill: "#f59e0b",
                  fontSize: isMobile ? 10 : 12,
                  position: "insideTopRight",
                }}
              />
              <Bar dataKey="allIn" name="allIn" radius={[4, 4, 0, 0]}>
                {chart.data.map((point) => (
                  <Cell
                    key={point.timestamp}
                    fill={priceColor(point.allIn, chart.average)}
                    opacity={point.isCurrent ? 1 : 0.82}
                  />
                ))}
              </Bar>
              <Line
                type="monotone"
                dataKey="spot"
                name="spot"
                stroke="#fde68a"
                dot={false}
                strokeWidth={2}
              />
              {chart.currentIndex >= 0 && (
                <ReferenceLine
                  x={chart.data[chart.currentIndex]?.time}
                  stroke="#e2e8f0"
                  strokeDasharray="2 4"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
