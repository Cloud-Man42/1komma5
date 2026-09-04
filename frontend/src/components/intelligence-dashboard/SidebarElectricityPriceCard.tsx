"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Label,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import type { EnergyStrategyCurrent, PricePeriodSnapshot } from "@/lib/api";
import {
  buildSidebarElectricityPriceModelFromImportPeriods,
  enrichPointsWithSegments,
  lineColorForOre,
} from "@/lib/sidebarElectricityPrice";
import { toOrePerKwh } from "@/lib/prices";

function formatTripleOre(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(toOrePerKwh(value))} öre`;
}

export function SidebarElectricityPriceCard({
  periods,
  timezone,
  strategy,
}: {
  periods: PricePeriodSnapshot[] | null;
  timezone: string;
  strategy?: EnergyStrategyCurrent | null;
}) {
  const model = useMemo(
    () => (periods ? buildSidebarElectricityPriceModelFromImportPeriods(periods, timezone) : null),
    [periods, timezone],
  );
  const chartData = useMemo(
    () => (model ? enrichPointsWithSegments(model.points) : []),
    [model],
  );

  if (!model) {
    return (
      <section className="idash-elprice-card" data-testid="sidebar-elprice-card">
        <header className="idash-elprice-header">
          <div>
            <h2>ELPRIS IDAG</h2>
            <p className="idash-elprice-subtitle">Faktiskt köp · 1komma5</p>
          </div>
          <span className="idash-elprice-live">
            <span className="idash-elprice-live-dot" aria-hidden="true" />
            LIVE
          </span>
        </header>
        <p className="idash-elprice-empty">Inga elpriser tillgängliga just nu.</p>
      </section>
    );
  }

  const currentPoint = model.points[model.currentIndex];
  const minOre = model.lowestOre;
  const maxOre = model.highestOre;

  return (
    <section className="idash-elprice-card" data-testid="sidebar-elprice-card">
      <header className="idash-elprice-header">
        <div>
          <h2>ELPRIS IDAG</h2>
          <p className="idash-elprice-subtitle">Faktiskt köp · 1komma5</p>
        </div>
        <span className="idash-elprice-live">
          <span className="idash-elprice-live-dot" aria-hidden="true" />
          LIVE
        </span>
      </header>

      <div className="idash-elprice-chart-wrap">
        <p className="idash-elprice-y-label">öre/kWh</p>
        <ResponsiveContainer width="100%" height={132}>
          <ComposedChart data={chartData} margin={{ top: 18, right: 6, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.08)" vertical={false} />
            <XAxis
              type="number"
              dataKey="hour"
              domain={[0, 24]}
              ticks={[0, 6, 12, 18, 24]}
              tickFormatter={(value) => `${String(value).padStart(2, "0")}:00`}
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[model.yMin, model.yMax]}
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={28}
              tickFormatter={(value) => String(Math.round(Number(value)))}
            />
            {Array.from({ length: model.segmentCount }).map((_, seg) => (
              <Line
                key={`seg-${seg}`}
                type="monotone"
                dataKey={`seg${seg}`}
                stroke={lineColorForOre(
                  ((model.points[seg]?.ore ?? 0) + (model.points[seg + 1]?.ore ?? 0)) / 2,
                  minOre,
                  maxOre,
                )}
                strokeWidth={2.5}
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
            {currentPoint ? (
              <>
                <ReferenceLine
                  x={currentPoint.hour}
                  stroke="#4ade80"
                  strokeDasharray="4 4"
                  strokeOpacity={0.85}
                />
                <ReferenceDot
                  x={currentPoint.hour}
                  y={currentPoint.ore}
                  r={5}
                  fill="#4ade80"
                  stroke="#ecfccb"
                  strokeWidth={2}
                  ifOverflow="extendDomain"
                >
                  <Label
                    value={`NU\n${currentPoint.ore} öre`}
                    position="top"
                    offset={12}
                    fill="#4ade80"
                    fontSize={10}
                    fontWeight={700}
                  />
                </ReferenceDot>
              </>
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="idash-elprice-stats">
        <div className="idash-elprice-stat">
          <strong>{model.lowestOre} öre</strong>
          <span className="idash-elprice-stat-label is-low">Lägst</span>
        </div>
        <div className="idash-elprice-stat is-current">
          <strong>{model.currentOre} öre</strong>
          <span className="idash-elprice-stat-label">Nu</span>
        </div>
        <div className="idash-elprice-stat">
          <strong>{model.highestOre} öre</strong>
          <span className="idash-elprice-stat-label is-high">Högst</span>
        </div>
      </div>

      {model.trend ? (
        <div
          className={`idash-elprice-trend ${model.trend.direction === "rising" ? "is-rising" : model.trend.direction === "falling" ? "is-falling" : ""}`.trim()}
          data-testid="sidebar-elprice-trend"
        >
          <span className="idash-elprice-trend-icon" aria-hidden="true">
            {model.trend.direction === "rising" ? "↑" : model.trend.direction === "falling" ? "↓" : "→"}
          </span>
          <span>
            {model.trend.direction === "falling" ? (
              <>
                Pris sjunker · <em>{model.trend.deltaOre} öre</em> billigare kl. {model.trend.atHourLabel}
              </>
            ) : model.trend.direction === "rising" ? (
              <>
                Pris stiger · <em>{model.trend.deltaOre} öre</em> dyrare kl. {model.trend.atHourLabel}
              </>
            ) : (
              model.trend.text
            )}
          </span>
        </div>
      ) : null}

      {strategy ? (
        <div className="idash-elprice-triple" data-testid="sidebar-elprice-triple">
          <div>
            <span>Nord Pool</span>
            <strong>{formatTripleOre(strategy.market_price_sek_kwh)}</strong>
          </div>
          <div>
            <span>Köp</span>
            <strong>{formatTripleOre(strategy.import_price_sek_kwh)}</strong>
          </div>
          <div>
            <span>Sälj</span>
            <strong>{formatTripleOre(strategy.export_price_sek_kwh)}</strong>
          </div>
        </div>
      ) : null}
    </section>
  );
}
