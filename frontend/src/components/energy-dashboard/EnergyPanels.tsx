"use client";

import type { CSSProperties, ReactNode } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";
import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";
import { formatWatts, type PeakPeriod, type PeakReading, type Reading } from "@/lib/api";
import {
  batteryFlowState,
  computeEnergyFlows,
  computeWireFlows,
  isFlowActive,
  normalizeFlowValues,
  readingToFlowValues,
} from "@/lib/energyFlow";
import {
  buildEnergyBalance,
  formatEnergyKwh,
  formatEnergyKw,
  formatPeakPeriod,
  peakSummary,
  type EnergyFlowChartPoint,
  type EnergyLiveMetrics,
  type EnergyTodayMetrics,
} from "./energyDashboardHelpers";

function MetricCard({
  title,
  icon,
  value,
  subtext,
  detail,
  accent,
  sparkValues,
}: {
  title: string;
  icon: ReactNode;
  value: string;
  subtext: string;
  detail?: string;
  accent: string;
  sparkValues: number[];
}) {
  return (
    <article className="enrg-metric-card" style={{ "--enrg-accent": accent } as CSSProperties}>
      <div className="enrg-metric-spark-bg" aria-hidden="true">
        <Sparkline values={sparkValues} color={accent} className="enrg-metric-spark" />
      </div>
      <div className="enrg-metric-head">
        <span className="enrg-metric-icon" style={{ color: accent }} aria-hidden="true">
          {icon}
        </span>
        <p className="enrg-metric-label">{title}</p>
      </div>
      <strong className="enrg-metric-value">{value}</strong>
      <p className="enrg-metric-sub">{subtext}</p>
      {detail ? <p className="enrg-metric-detail">{detail}</p> : null}
    </article>
  );
}

export function EnergyMetricStrip({
  live,
  today,
  sparkSolar,
  sparkConsumption,
  sparkBattery,
  sparkGrid,
}: {
  live: EnergyLiveMetrics;
  today: EnergyTodayMetrics;
  sparkSolar: number[];
  sparkConsumption: number[];
  sparkBattery: number[];
  sparkGrid: number[];
}) {
  const batteryLabel =
    live.batteryDirection === "charging"
      ? "Laddar"
      : live.batteryDirection === "discharging"
        ? "Urladdar"
        : "Vila";
  const gridLabel = live.gridNetW >= 25 ? "Exporterar" : live.gridNetW <= -25 ? "Importerar" : "Balanserat";

  return (
    <div className="enrg-metric-strip" data-testid="energy-metric-strip">
      <MetricCard
        title="SOLPRODUKTION"
        accent="#fbbf24"
        icon="☀"
        value={formatEnergyKw(live.solarW)}
        subtext="Just nu"
        detail={`Dag totalt ${formatEnergyKwh(today.producedKwh)}`}
        sparkValues={sparkSolar.length > 1 ? sparkSolar : [0, live.solarW]}
      />
      <MetricCard
        title="HUSFÖRBRUKNING"
        accent="#38bdf8"
        icon="⌂"
        value={formatEnergyKw(live.consumptionW)}
        subtext="Just nu"
        detail={`Dag totalt ${formatEnergyKwh(today.consumedKwh)}`}
        sparkValues={sparkConsumption.length > 1 ? sparkConsumption : [0, live.consumptionW]}
      />
      <MetricCard
        title="BATTERI"
        accent="#c084fc"
        icon="▮"
        value={formatEnergyKw(live.batteryW)}
        subtext={live.batterySocPct != null ? `${Math.round(live.batterySocPct)}% SoC · ${batteryLabel}` : batteryLabel}
        detail={`Laddning ${formatEnergyKwh(today.batteryChargeKwh)} · Urladdning ${formatEnergyKwh(today.batteryDischargeKwh)}`}
        sparkValues={sparkBattery.length > 1 ? sparkBattery : [0, live.batteryW]}
      />
      <MetricCard
        title="NETTO MOT NÄT"
        accent="#4ade80"
        icon="⇄"
        value={formatEnergyKw(Math.abs(live.gridNetW))}
        subtext={gridLabel}
        detail={`Export ${formatEnergyKwh(today.exportedKwh)} · Import ${formatEnergyKwh(today.importedKwh)}`}
        sparkValues={sparkGrid.length > 1 ? sparkGrid : [0, live.gridNetW]}
      />
      <EnergyBalanceDonut today={today} />
    </div>
  );
}

function EnergyBalanceDonut({ today }: { today: EnergyTodayMetrics }) {
  const balance = buildEnergyBalance(today);
  const radius = 52;
  const stroke = 12;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <article className="enrg-balance-card" data-testid="energy-balance-donut">
      <p className="enrg-metric-label">ENERGIBALANS IDAG</p>
      <div className="enrg-balance-body">
        <svg viewBox="0 0 140 140" className="enrg-balance-chart" aria-hidden="true">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth={stroke} />
          {balance.slices.map((slice) => {
            const dash = (slice.pct / 100) * circumference;
            const current = offset;
            offset += dash;
            return (
              <circle
                key={slice.id}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={stroke}
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-current}
                transform="rotate(-90 70 70)"
              />
            );
          })}
        </svg>
        <div className="enrg-balance-center">
          <strong>{balance.centerValue}</strong>
          <span>{balance.centerLabel}</span>
        </div>
      </div>
      <ul className="enrg-balance-legend">
        {balance.slices.map((slice) => (
          <li key={slice.id}>
            <span className="enrg-balance-dot" style={{ background: slice.color }} />
            <span>{slice.label}</span>
            <strong>
              {Math.round(slice.pct)}% · {formatEnergyKwh(slice.kwh)}
            </strong>
          </li>
        ))}
      </ul>
    </article>
  );
}

const ENERGY_FLOW_CHART_LEGEND = [
  { id: "solar", label: "Solproduktion", color: "#fbbf24", kind: "area" as const },
  { id: "charge", label: "Batteriladdning", color: "#c084fc", kind: "area" as const },
  { id: "consumption", label: "Husförbrukning", color: "#38bdf8", kind: "area" as const },
  { id: "discharge", label: "Batteriurladdning", color: "#f472b6", kind: "area" as const },
  { id: "net", label: "Netto (sol − förbrukning ± batteri)", color: "#f8fafc", kind: "line" as const },
];

export function EnergyFlowChartPanel({
  series,
  bucketMinutes,
  onBucketChange,
}: {
  series: EnergyFlowChartPoint[];
  bucketMinutes: number;
  onBucketChange: (bucket: 5 | 15 | 60) => void;
}) {
  return (
    <section className="enrg-panel enrg-flow-chart-panel" data-testid="energy-flow-chart">
      <header className="enrg-panel-header">
        <div>
          <h2 className="enrg-panel-title">ENERGIFLÖDE – IDAG</h2>
        </div>
        <div className="enrg-resolution-tabs" role="tablist" aria-label="Upplösning">
          {([5, 15, 60] as const).map((bucket) => (
            <button
              key={bucket}
              type="button"
              role="tab"
              aria-selected={bucketMinutes === bucket}
              className={bucketMinutes === bucket ? "enrg-resolution-tab enrg-resolution-tab-active" : "enrg-resolution-tab"}
              onClick={() => onBucketChange(bucket)}
            >
              {bucket === 60 ? "1h" : `${bucket}m`}
            </button>
          ))}
        </div>
      </header>
      <ul className="enrg-flow-legend" aria-label="Förklaring av kurvor" data-testid="energy-flow-legend">
        {ENERGY_FLOW_CHART_LEGEND.map((item) => (
          <li key={item.id}>
            <span
              className={`enrg-flow-legend-swatch ${item.kind === "line" ? "enrg-flow-legend-swatch-line" : ""}`.trim()}
              style={{ "--enrg-swatch-color": item.color } as CSSProperties}
              aria-hidden="true"
            />
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
      {series.length === 0 ? (
        <p className="enrg-muted">Ingen historik tillgänglig för vald period.</p>
      ) : (
        <div className="enrg-chart-wrap">
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                width={42}
                domain={["auto", "auto"]}
                tickFormatter={(v) => `${v}`}
                label={{ value: "kW", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid rgba(148,163,184,0.2)",
                  borderRadius: 10,
                  fontSize: 12,
                }}
              />
              <Area type="monotone" dataKey="solarKw" stackId="pos" fill="#fbbf24" stroke="#fbbf24" fillOpacity={0.35} name="Sol" />
              <Area type="monotone" dataKey="batteryChargeKw" stackId="pos" fill="#c084fc" stroke="#c084fc" fillOpacity={0.35} name="Batteriladdning" />
              <Area type="monotone" dataKey="consumptionKw" stackId="neg" fill="#38bdf8" stroke="#38bdf8" fillOpacity={0.35} name="Förbrukning" />
              <Area type="monotone" dataKey="batteryDischargeKw" stackId="neg" fill="#f472b6" stroke="#f472b6" fillOpacity={0.35} name="Batteriurladdning" />
              <Line type="monotone" dataKey="netKw" stroke="#f8fafc" strokeWidth={2} dot={false} name="Netto" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export function EnergyBatteryPanel({
  live,
  today,
  socSeries,
}: {
  live: EnergyLiveMetrics;
  today: EnergyTodayMetrics;
  socSeries: number[];
}) {
  const soc = live.batterySocPct ?? 0;
  const netBatteryKw = today.batteryChargeKwh - today.batteryDischargeKwh;

  return (
    <section className="enrg-panel enrg-battery-panel" data-testid="energy-battery-panel">
      <h2 className="enrg-panel-title">BATTERI – IDAG</h2>
      <div className="enrg-battery-gauge-wrap">
        <CircularGauge
          value={soc}
          label={`${Math.round(soc)}%`}
          sublabel="SoC"
          color="#4ade80"
          size={168}
        />
      </div>
      <dl className="enrg-battery-stats">
        <div>
          <dt>Laddning</dt>
          <dd>{formatEnergyKwh(today.batteryChargeKwh)}</dd>
        </div>
        <div>
          <dt>Urladdning</dt>
          <dd>{formatEnergyKwh(today.batteryDischargeKwh)}</dd>
        </div>
        <div>
          <dt>Netto</dt>
          <dd>
            {netBatteryKw >= 0 ? "+" : "−"}
            {formatEnergyKwh(Math.abs(netBatteryKw))}
          </dd>
        </div>
      </dl>
      <div className="enrg-soc-spark-wrap" aria-hidden="true">
        <Sparkline values={socSeries.length > 1 ? socSeries : [soc, soc]} color="#4ade80" className="enrg-soc-spark" />
      </div>
    </section>
  );
}

function QuickFlowNode({
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
    <div className={`enrg-quick-node enrg-quick-node-${tone}`}>
      <span className="enrg-quick-icon" aria-hidden="true">
        {icon}
      </span>
      <strong>{label}</strong>
      <span className="enrg-quick-value">{value}</span>
      {sub ? <span className="enrg-quick-sub">{sub}</span> : null}
    </div>
  );
}

function QuickFlowLine({ active, tone }: { active: boolean; tone: string }) {
  return (
    <div className={`enrg-quick-line ${active ? "enrg-quick-line-active" : ""}`} data-tone={tone}>
      <span className="enrg-quick-line-glow" />
    </div>
  );
}

export function EnergyQuickOverviewPanel({ reading }: { reading: Reading | null }) {
  if (!reading) {
    return (
      <section className="enrg-panel enrg-quick-panel" data-testid="energy-quick-overview">
        <h2 className="enrg-panel-title">SNABBÖVERSIKT JUST NU</h2>
        <p className="enrg-muted">Väntar på live-data…</p>
      </section>
    );
  }

  const values = normalizeFlowValues(readingToFlowValues(reading));
  const wires = computeWireFlows(values);
  const flows = computeEnergyFlows(values);
  const battery = batteryFlowState(values.batteryPowerW);
  const gridExport = wires.gridExportW >= 25;
  const gridImport = wires.gridImportW >= 25;

  return (
    <section className="enrg-panel enrg-quick-panel" data-testid="energy-quick-overview">
      <h2 className="enrg-panel-title">SNABBÖVERSIKT JUST NU</h2>
      <div className="enrg-quick-flow">
        <QuickFlowNode tone="solar" label="Sol" icon="☀" value={formatWatts(wires.solarInverterW)} />
        <QuickFlowLine active={isFlowActive(flows.solarToHouse)} tone="solar" />
        <QuickFlowNode tone="house" label="Hus" icon="⌂" value={formatWatts(wires.houseFeedW)} />
        <QuickFlowLine
          active={isFlowActive(flows.batteryToHouse) || isFlowActive(flows.solarToBattery)}
          tone="battery"
        />
        <QuickFlowNode
          tone="battery"
          label="Batteri"
          icon="▮"
          value={formatWatts(Math.abs(values.batteryPowerW))}
          sub={
            battery.mode === "discharging"
              ? "Urladdning"
              : battery.mode === "charging"
                ? "Laddning"
                : `${Math.round(values.batterySocPct)}% SoC`
          }
        />
        <QuickFlowLine active={gridExport || gridImport} tone="grid" />
        <QuickFlowNode
          tone="grid"
          label="Nät"
          icon="⇄"
          value={formatWatts(gridExport ? wires.gridExportW : wires.gridImportW)}
          sub={gridExport ? "Export" : gridImport ? "Import" : "Balans"}
        />
      </div>
    </section>
  );
}

const PERIOD_LABELS: Record<PeakPeriod, string> = {
  day: "Dagar",
  month: "Månader",
  year: "År",
};

export function EnergyPeaksPanel({
  peaks,
  period,
  onPeriodChange,
  year,
  onYearChange,
  availableYears,
  loading,
  error,
}: {
  peaks: PeakReading[];
  period: PeakPeriod;
  onPeriodChange: (period: PeakPeriod) => void;
  year: number;
  onYearChange: (year: number) => void;
  availableYears: number[];
  loading: boolean;
  error: string | null;
}) {
  const summary = peakSummary(peaks);
  const todayKey = new Date().toISOString().slice(0, 10);

  return (
    <section className="enrg-panel enrg-peaks-panel" id="enrg-peaks" data-testid="energy-peaks-panel">
      <header className="enrg-peaks-header">
        <div>
          <h2 className="enrg-panel-title">PEAKVÄRDEN</h2>
          <p className="enrg-muted">Högsta uppmätta effekt per period.</p>
        </div>
        <dl className="enrg-peaks-summary-inline">
          <div>
            <dt>Högsta Solpeak</dt>
            <dd>{formatWatts(summary.solar)}</dd>
          </div>
          <div>
            <dt>Högsta Förbrukning</dt>
            <dd>{formatWatts(summary.consumption)}</dd>
          </div>
          <div>
            <dt>Högsta Laddning</dt>
            <dd>{formatWatts(summary.charge)}</dd>
          </div>
          <div>
            <dt>Högsta Urladdning</dt>
            <dd>{formatWatts(summary.discharge)}</dd>
          </div>
        </dl>
      </header>

      <div className="enrg-peaks-controls">
        <div className="enrg-peaks-tabs" role="tablist" aria-label="Tidsperiod">
          {(Object.keys(PERIOD_LABELS) as PeakPeriod[]).map((value) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={period === value}
              className={period === value ? "enrg-peaks-tab enrg-peaks-tab-active" : "enrg-peaks-tab"}
              onClick={() => onPeriodChange(value)}
            >
              {PERIOD_LABELS[value]}
            </button>
          ))}
        </div>
        {period !== "year" ? (
          <label className="enrg-peaks-year">
            <span>År</span>
            <select aria-label="Välj år" value={year} onChange={(e) => onYearChange(Number(e.target.value))}>
              {(availableYears.length > 0 ? availableYears : [year]).map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {loading ? (
        <p className="enrg-muted">Läser peakvärden…</p>
      ) : error ? (
        <p className="enrg-error" role="alert">
          {error}
        </p>
      ) : peaks.length === 0 ? (
        <p className="enrg-muted">Det finns inga peakvärden för den valda perioden.</p>
      ) : (
        <div className="enrg-peaks-table-wrap">
          <table className="enrg-peaks-table">
            <thead>
              <tr>
                <th scope="col">{period === "day" ? "Datum" : period === "month" ? "Månad" : "År"}</th>
                <th scope="col">Solproduktion (peak)</th>
                <th scope="col">Husförbrukning (peak)</th>
                <th scope="col">Batteriladdning (peak)</th>
                <th scope="col">Batteriurladdning (peak)</th>
              </tr>
            </thead>
            <tbody>
              {[...peaks].reverse().map((peak) => (
                <tr
                  key={peak.period_start}
                  className={period === "day" && peak.period_start === todayKey ? "enrg-peaks-row-today" : undefined}
                >
                  <th scope="row">{formatPeakPeriod(peak.period_start, period)}</th>
                  <td>{formatWatts(peak.solar_production_w)}</td>
                  <td>{formatWatts(peak.consumption_w ?? 0)}</td>
                  <td>{formatWatts(peak.battery_charge_w)}</td>
                  <td>{formatWatts(peak.battery_discharge_w)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function EnergyPlaceholderSection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="enrg-panel enrg-placeholder-panel">
      <h2 className="enrg-panel-title">{title}</h2>
      <p className="enrg-muted">{description}</p>
    </section>
  );
}
