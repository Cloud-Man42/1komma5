"use client";

import { useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";
import { formatPriceOre } from "./economyDashboardHelpers";
import type { DailyCostPoint } from "./economyDashboardHelpers";
import { formatEconomyKr } from "./economyDashboardHelpers";
import { navigateEconomySection } from "./economySection";

function formatKrPerKwh(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(2)} kr/kWh`;
}

export function EconomyCostOverviewChart({ series }: { series: DailyCostPoint[] }) {
  const [mode, setMode] = useState<"kr" | "kwh">("kr");
  const [hovered, setHovered] = useState<DailyCostPoint | null>(null);  const width = 560;
  const height = 220;
  const pad = { top: 16, right: 12, bottom: 28, left: 40 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  const chart = useMemo(() => {
    if (series.length === 0) return null;
    const values = series.flatMap((p) =>
      mode === "kr"
        ? [p.purchasedSek + p.gridFeeSek + p.taxSek, Math.abs(p.soldSek), p.netSek]
        : [p.importedKwh, p.exportedKwh],
    );
    const max = Math.max(...values, 1);
    const min = Math.min(...series.map((p) => (mode === "kr" ? p.soldSek : 0)), 0);
    const range = max - min || 1;
    const barW = innerW / series.length - 4;

    const y = (v: number) => pad.top + innerH - ((v - min) / range) * innerH;
    const x = (i: number) => pad.left + i * (innerW / series.length) + 2;

    const bars = series.map((point, i) => {
      if (mode === "kwh") {
        const importH = ((point.importedKwh - min) / range) * innerH;
        const exportH = ((point.exportedKwh - min) / range) * innerH;
        return (
          <g
            key={point.date}
            onMouseEnter={() => setHovered(point)}
            onMouseLeave={() => setHovered(null)}
            tabIndex={0}
            role="graphics-symbol"
          >
            <rect x={x(i)} y={y(point.importedKwh)} width={barW / 2} height={importH} fill="#a78bfa" rx="2" />
            <rect x={x(i) + barW / 2} y={y(point.exportedKwh)} width={barW / 2} height={exportH} fill="#4ade80" rx="2" />
          </g>
        );      }
      const stackTop = point.purchasedSek + point.gridFeeSek + point.taxSek;
      const purchasedH = (point.purchasedSek / range) * innerH;
      const gridH = (point.gridFeeSek / range) * innerH;
      const taxH = (point.taxSek / range) * innerH;
      const soldH = (Math.abs(point.soldSek) / range) * innerH;
      const baseY = y(0);
      let cursor = baseY;
      return (
        <g
          key={point.date}
          onMouseEnter={() => setHovered(point)}
          onMouseLeave={() => setHovered(null)}
          onFocus={() => setHovered(point)}
          onBlur={() => setHovered(null)}
          tabIndex={0}
          role="graphics-symbol"
          aria-label={`${point.dayLabel}: nettokostnad ${formatEconomyKr(point.netSek)}`}
        >
          <rect x={x(i)} y={cursor - purchasedH} width={barW} height={purchasedH} fill="#a78bfa" />          {(() => {
            cursor -= purchasedH;
            return null;
          })()}
          <rect x={x(i)} y={baseY - purchasedH - gridH} width={barW} height={gridH} fill="#38bdf8" />
          <rect x={x(i)} y={baseY - stackTop} width={barW} height={taxH} fill="#2dd4bf" />
          <rect x={x(i)} y={baseY} width={barW} height={soldH} fill="#4ade80" opacity="0.85" />
        </g>
      );
    });

    const linePoints = series
      .map((p, i) => {
        const val = mode === "kr" ? p.netSek : p.importedKwh - p.exportedKwh;
        return `${x(i) + barW / 2},${y(val)}`;
      })
      .join(" ");

    return { bars, linePoints, max, min };
  }, [innerH, innerW, mode, pad.left, pad.top, series]);

  return (
    <article className="edash-panel edash-panel-chart" data-testid="economy-cost-chart">
      <header className="edash-panel-head">
        <h3>KOSTNADSÖVERSIKT</h3>
        <div className="edash-toggle" role="group" aria-label="Visningsenhet">
          <button type="button" className={mode === "kr" ? "is-active" : ""} onClick={() => setMode("kr")}>
            kr
          </button>
          <button type="button" className={mode === "kwh" ? "is-active" : ""} onClick={() => setMode("kwh")}>
            kWh
          </button>
        </div>
      </header>
      <div className="edash-chart-legend">
        {mode === "kr" ? (
          <>
            <span><i style={{ background: "#a78bfa" }} />Köpt el</span>
            <span><i style={{ background: "#38bdf8" }} />Nätavgift</span>
            <span><i style={{ background: "#2dd4bf" }} />Skatt</span>
            <span><i style={{ background: "#4ade80" }} />Såld el</span>
            <span><i style={{ background: "#fb923c" }} />Nettokostnad</span>
          </>
        ) : (
          <>
            <span><i style={{ background: "#a78bfa" }} />Import</span>
            <span><i style={{ background: "#4ade80" }} />Export</span>
          </>
        )}
      </div>
      {series.length === 0 ? (
        <p className="edash-muted">Ingen kostnadsdata för vald period.</p>
      ) : (
        <>
          {hovered && mode === "kr" ? (
            <div className="edash-chart-tooltip" data-testid="economy-chart-tooltip">
              <strong>{hovered.dayLabel}</strong>
              <p>Köpt el: {hovered.importedKwh.toFixed(1)} kWh · {formatEconomyKr(hovered.purchasedSek)}</p>
              <p>Nätavgift: {formatEconomyKr(hovered.gridFeeSek)}</p>
              <p>Skatt: {formatEconomyKr(hovered.taxSek)}</p>
              <p>Såld el: −{formatEconomyKr(Math.abs(hovered.soldSek))}</p>
              <p>Nettokostnad: {formatEconomyKr(hovered.netSek)}</p>
              <p>Snittpris: {formatKrPerKwh(hovered.effectivePriceKrKwh)}</p>
            </div>
          ) : null}
          <svg viewBox={`0 0 ${width} ${height}`} className="edash-cost-chart" aria-label="Kostnadsöversikt">
            {chart?.bars}
            {chart?.linePoints ? (
              <polyline points={chart.linePoints} fill="none" stroke="#fb923c" strokeWidth="2.5" />
            ) : null}
            {series.map((point, i) => (
              <text
                key={`lbl-${point.date}`}
                x={pad.left + i * (innerW / series.length) + innerW / series.length / 2}
                y={height - 6}
                textAnchor="middle"
                className="edash-chart-axis-label"
              >
                {point.label}
              </text>
            ))}
          </svg>
        </>
      )}    </article>
  );
}

export function EconomyDonutPanel({
  totalSek,
  slices,
}: {
  totalSek: number;
  slices: { label: string; pct: number; color: string }[];
}) {
  const size = 160;
  const stroke = 22;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <article className="edash-panel edash-panel-donut" data-testid="economy-donut">
      <h3>KOSTNADSFÖRDELNING</h3>
      <div className="edash-donut-wrap">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth={stroke} />
          {slices.map((slice) => {
            const dash = (slice.pct / 100) * circumference;
            const el = (
              <circle
                key={slice.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={stroke}
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-offset}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
              />
            );
            offset += dash;
            return el;
          })}
        </svg>
        <div className="edash-donut-center">
          <strong>{formatEconomyKr(totalSek)}</strong>
          <span>Totalt</span>
        </div>
      </div>
      <ul className="edash-donut-legend">
        {slices.map((slice) => (
          <li key={slice.label}>
            <i style={{ background: slice.color }} />
            <span>{slice.label}</span>
            <em>{Math.round(slice.pct)}%</em>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function EconomyPricePanel({
  siteSlug,
  spotOre,
  purchaseOre,
  exportOre,
  cheapestOre,
  cheapestAt,
  expensiveOre,
  expensiveAt,
}: {
  siteSlug: string;
  spotOre: number | null;
  purchaseOre: number | null;
  exportOre: number | null;
  cheapestOre: number | null;
  cheapestAt: string | null;
  expensiveOre: number | null;
  expensiveAt: string | null;
}) {
  return (
    <article className="edash-panel edash-panel-prices" data-testid="economy-price-panel">
      <h3>ELPRIS ANALYS</h3>
      <dl className="edash-price-list">
        <div><dt>Spotpris</dt><dd>{formatPriceOre(spotOre)}</dd></div>
        <div><dt>Köpt pris</dt><dd>{formatPriceOre(purchaseOre)}</dd></div>
        <div><dt>Sålt pris</dt><dd>{formatPriceOre(exportOre)}</dd></div>
      </dl>
      <div className="edash-price-extremes">
        <p><span>Billigaste timme</span><strong>{formatPriceOre(cheapestOre)}</strong><em>{cheapestAt ?? "—"}</em></p>
        <p><span>Dyraste timme</span><strong>{formatPriceOre(expensiveOre)}</strong><em>{expensiveAt ?? "—"}</em></p>
      </div>
      <button
        type="button"
        className="edash-link-btn"
        onClick={() => navigateEconomySection(siteSlug, "prices")}
      >
        Visa prisdetaljer ›
      </button>
    </article>
  );
}
