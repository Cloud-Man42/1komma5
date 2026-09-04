"use client";

import Image from "next/image";
import type { CSSProperties, FormEvent } from "react";
import { useEffect, useState } from "react";
import { DeadlineInput } from "@/components/DeadlineInput";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { HaloPowerIndicator } from "@/components/HaloPowerIndicator";
import type {
  EnergyReasoning,
  EvBridgeStatus,
  EvCharger,
  EvChargingSavings,
  EvChargingSession,
  EvChargingStats,
  EvSolarChargingPlan,
} from "@/lib/api";
import { controlEvCharger, formatWatts, setEvChargerOverride, updateEvCharger } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";
import { EV_HALO_PRODUCT } from "@/lib/evScenePhoto";
import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";
import {
  averageSessionCostOre,
  buildPlanWindows,
  deadlineHeaderLabel,
  formatEvCurrent,
  formatEvDuration,
  formatEvKwh,
  formatEvPowerW,
  formatEvSessionTime,
  formatMonthCost,
  isHaloCharger,
  modeLabel,
  nextChargeWindowLabel,
  priceTierDisplay,
  sessionAveragePowerW,
  sessionSourceLabel,
  totalChargeMinutesToday,
  uplinkLabel,
  EV_MODE_LABELS,
  isPriceOnlyMode,
  type EvEnergyMixSlice,
  type EvHourlySourcePoint,
  type EvPlanWindow,
  type EvPowerChartPoint,
  type EvSavingsChartPoint,
  type EvStatsPeriod,
} from "./evDashboardHelpers";

export function EvHeaderChips({
  charger,
  bridge,
  reasoning,
}: {
  charger: EvCharger;
  bridge: EvBridgeStatus | null;
  reasoning: EnergyReasoning | null;
}) {
  const smartOn = charger.charging_mode !== "PAUSED";
  return (
    <div className="evdash-header-chips" data-testid="ev-header-chips">
      <div>
        <p className="evdash-chip-label">KLAR SENAST</p>
        <strong>{deadlineHeaderLabel(charger.deadline_at)}</strong>
        {charger.departure_time ? <span>Imorgon {charger.departure_time}</span> : null}
      </div>
      <div>
        <p className="evdash-chip-label">SMART LADDNING</p>
        <strong className={smartOn ? "evdash-text-good" : ""}>{smartOn ? "På" : "Av"}</strong>
        <span>{bridge?.active_policy ? "Aktiv policy" : "—"}</span>
      </div>
      <div>
        <p className="evdash-chip-label">TILLGÄNGLIG STRÖM</p>
        <strong>{formatEvCurrent(charger.max_current_a)}</strong>
        <span>Max {formatEvCurrent(charger.max_current_a)}</span>
      </div>
      {reasoning?.vehicle_target_soc_pct != null ? (
        <div>
          <p className="evdash-chip-label">MÅL-SOC</p>
          <strong>{Math.round(reasoning.vehicle_target_soc_pct)}%</strong>
        </div>
      ) : null}
    </div>
  );
}

export function EvPowerPanel({
  charger,
  powerChart,
  maxPowerKw,
}: {
  charger: EvCharger;
  powerChart: EvPowerChartPoint[];
  maxPowerKw: number;
}) {
  const spark = powerChart.map((p) => p.powerKw * 1000);
  return (
    <section className="evdash-panel evdash-power-panel" data-testid="ev-power-panel">
      <header className="evdash-panel-head">
        <div>
          <p className="evdash-panel-kicker">AKTUELL EFFEKT</p>
          <strong className="evdash-power-value">{formatEvPowerW(charger.power_w)}</strong>
        </div>
        <div className="evdash-max-badge">
          <span aria-hidden="true">★</span>
          Max idag: {maxPowerKw.toFixed(1)} kW
        </div>
      </header>
      {powerChart.length > 1 ? (
        <div className="evdash-power-chart">
          <ResponsiveContainer width="100%" height={120}>
            <ComposedChart data={powerChart}>
              <defs>
                <linearGradient id="evPowerFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4ade80" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#4ade80" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="powerKw" stroke="#4ade80" fill="url(#evPowerFill)" strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Sparkline values={spark.length > 1 ? spark : [0, charger.power_w ?? 0]} color="#4ade80" className="evdash-power-spark" />
      )}
    </section>
  );
}

export function EvHardwarePanel({
  charger,
  bridge,
}: {
  charger: EvCharger;
  bridge: EvBridgeStatus | null;
}) {
  const showHalo = isHaloCharger(charger);
  return (
    <section className="evdash-panel evdash-hardware-panel" data-testid="ev-hardware-panel">
      <div className={`evdash-hardware-body${showHalo ? "" : " evdash-hardware-body--solo"}`}>
        {showHalo ? (
          <>
            <div className="evdash-halo-wrap">
              <Image
                src={EV_HALO_PRODUCT}
                alt="Charge Amps Halo"
                width={280}
                height={200}
                className="evdash-halo-image"
              />
            </div>
            <div className="evdash-hardware-indicator">
              <HaloPowerIndicator charger={charger} />
            </div>
          </>
        ) : null}
        <dl className="evdash-spec-list">
          <div><dt>Läge</dt><dd>{modeLabel(charger.charging_mode)}</dd></div>
          <div><dt>Status</dt><dd>{bridge?.display_status_sv ?? charger.smart_charging_state ?? "—"}</dd></div>
          <div><dt>Ansluten bil</dt><dd>{bridge?.vehicle_connected ? "Inkoppad" : "Ej inkopplad"}</dd></div>
          <div><dt>Senast använd</dt><dd>{charger.last_bridge_run_at ? formatEvSessionTime(charger.last_bridge_run_at) : "—"}</dd></div>
          <div><dt>Säkring / Ström</dt><dd>{formatEvCurrent(charger.max_current_a)}</dd></div>
          <div><dt>Tillämpad ström</dt><dd>{formatEvCurrent(bridge?.applied_current_a ?? charger.last_applied_current_a)}</dd></div>
          <div><dt>Uplink</dt><dd>{uplinkLabel(charger, bridge?.stale ?? null)}</dd></div>
        </dl>
      </div>
    </section>
  );
}

export function EvWaitingPanel({
  reasoning,
  plan,
}: {
  reasoning: EnergyReasoning | null;
  plan: EvSolarChargingPlan | null;
}) {
  const price = priceTierDisplay(reasoning);
  const message =
    reasoning?.decision_reason_sv ??
    plan?.explanation_sv ??
    "Väntar på bil eller bättre laddförutsättningar.";
  const solarWindow =
    plan?.expected_solar_window_start && plan.expected_solar_window_end
      ? `${new Date(plan.expected_solar_window_start).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" })} – ${new Date(plan.expected_solar_window_end).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" })}`
      : "—";

  return (
    <section className="evdash-panel evdash-waiting-panel" data-testid="ev-waiting-panel">
      <h2 className="evdash-panel-title">VÄNTAR PÅ BIL</h2>
      <p className="evdash-waiting-text">{message}</p>
      <ul className="evdash-status-rows">
        <li>
          <span className={`evdash-status-icon evdash-tone-${price.tone}`} aria-hidden="true">⚡</span>
          <div>
            <strong>Elprisnivå</strong>
            <span>{price.label}</span>
            <span>{price.detail}</span>
          </div>
        </li>
        <li>
          <span className="evdash-status-icon evdash-tone-green" aria-hidden="true">🍃</span>
          <div>
            <strong>Prioritet</strong>
            <span>{reasoning?.solar_first ? "Sol först" : "Nät vid billiga timmar"}</span>
          </div>
        </li>
        <li>
          <span className="evdash-status-icon" aria-hidden="true">◎</span>
          <div>
            <strong>Prognoskvalitet</strong>
            <span>{plan?.quality ?? "—"} {plan?.confidence != null ? `(${Math.round(plan.confidence)}%)` : ""}</span>
          </div>
        </li>
        <li>
          <span className="evdash-status-icon evdash-tone-yellow" aria-hidden="true">☀</span>
          <div>
            <strong>Förväntat solfönster</strong>
            <span>{solarWindow}</span>
          </div>
        </li>
      </ul>
      <div className="evdash-solar-window-gauge" aria-hidden="true">
        <strong>Solöverskott väntas</strong>
        <span>{solarWindow}</span>
      </div>
    </section>
  );
}

export function EvMiniStatsRow({
  dayStats,
  monthStats,
  co2SavedKg,
}: {
  dayStats: EvChargingStats | null;
  monthStats: EvChargingStats | null;
  co2SavedKg: number | null;
}) {
  return (
    <div className="evdash-mini-stats" data-testid="ev-mini-stats">
      <article>
        <span className="evdash-mini-icon evdash-tone-blue" aria-hidden="true">💧</span>
        <div>
          <p>Dagens laddat</p>
          <strong>{formatEvKwh(dayStats?.total_energy_kwh ?? 0)}</strong>
          <span>{dayStats?.session_count ?? 0} sessioner</span>
        </div>
      </article>
      <article>
        <span className="evdash-mini-icon evdash-tone-green" aria-hidden="true">📅</span>
        <div>
          <p>Denna månad</p>
          <strong>{formatEvKwh(monthStats?.total_energy_kwh ?? 0)}</strong>
          <span>{monthStats?.session_count ?? 0} sessioner</span>
        </div>
      </article>
      <article>
        <span className="evdash-mini-icon evdash-tone-yellow" aria-hidden="true">💰</span>
        <div>
          <p>Kostnad (månad)</p>
          <strong>{formatMonthCost(monthStats)}</strong>
          <span>Snitt {averageSessionCostOre(monthStats)}</span>
        </div>
      </article>
      <article>
        <span className="evdash-mini-icon evdash-tone-green" aria-hidden="true">🌿</span>
        <div>
          <p>CO₂ sparat (månad)</p>
          <strong>{co2SavedKg != null ? `${co2SavedKg.toFixed(1)} kg` : "—"}</strong>
          <span>vs bensinbil</span>
        </div>
      </article>
    </div>
  );
}

export function EvPlanPanel({ planWindows, plan }: { planWindows: EvPlanWindow[]; plan: EvSolarChargingPlan | null }) {
  return (
    <section className="evdash-panel evdash-plan-panel" data-testid="ev-plan-panel">
      <h2 className="evdash-panel-title">LADDPLAN – SMART LADDNING</h2>
      <div className="evdash-plan-body">
        <div className="evdash-plan-ring" aria-hidden="true">
          <strong>{nextChargeWindowLabel(plan)}</strong>
          <span>Nästa laddfönster</span>
        </div>
        <ul className="evdash-plan-legend">
          {(planWindows.length > 0 ? planWindows : buildPlanWindows(plan, null)).map((w) => (
            <li key={w.id}>
              <span className="evdash-plan-dot" style={{ background: w.color } as CSSProperties} />
              <span>{w.label}</span>
              <strong>{w.time}</strong>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function EvStatisticsPanel({
  hourlySources,
  period,
  onPeriodChange,
}: {
  hourlySources: EvHourlySourcePoint[];
  period: EvStatsPeriod;
  onPeriodChange: (period: EvStatsPeriod) => void;
}) {
  return (
    <section className="evdash-panel evdash-stats-panel" data-testid="ev-stats-panel">
      <header className="evdash-panel-head">
        <h2 className="evdash-panel-title">LADDNINGSSTATISTIK</h2>
        <div className="evdash-tabs" role="tablist" aria-label="Statistikperiod">
          {(["day", "week", "month", "year"] as EvStatsPeriod[]).map((p) => (
            <button
              key={p}
              type="button"
              role="tab"
              aria-selected={period === p}
              className={period === p ? "evdash-tab evdash-tab-active" : "evdash-tab"}
              onClick={() => onPeriodChange(p)}
            >
              {p === "day" ? "Dag" : p === "week" ? "Vecka" : p === "month" ? "Månad" : "År"}
            </button>
          ))}
        </div>
      </header>
      <div className="evdash-bar-chart-wrap">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={hourlySources}>
            <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={3} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} width={28} />
            <Tooltip />
            <Bar dataKey="solar" stackId="a" fill="#4ade80" name="Sol" />
            <Bar dataKey="battery" stackId="a" fill="#38bdf8" name="Batteri" />
            <Bar dataKey="gridCheap" stackId="a" fill="#fbbf24" name="Nät lågpris" />
            <Bar dataKey="gridExpensive" stackId="a" fill="#f87171" name="Nät dyrt" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="evdash-chart-legend" aria-label="Förklaring av staplar">
        <li><span style={{ background: "#4ade80" }} />Sol</li>
        <li><span style={{ background: "#38bdf8" }} />Batteri</li>
        <li><span style={{ background: "#fbbf24" }} />Nät lågpris</li>
        <li><span style={{ background: "#f87171" }} />Nät dyrt</li>
      </ul>
    </section>
  );
}

export function EvEnergyMixPanel({ slices, totalKwh }: { slices: EvEnergyMixSlice[]; totalKwh: number }) {
  const radius = 52;
  const stroke = 12;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <section className="evdash-panel evdash-mix-panel" data-testid="ev-energy-mix">
      <h2 className="evdash-panel-title">ENERGIFÖRDELNING – DAG</h2>
      <div className="evdash-mix-body">
        <svg viewBox="0 0 140 140" className="evdash-mix-chart" aria-hidden="true">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth={stroke} />
          {slices.map((slice) => {
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
        <div className="evdash-mix-center">
          <strong>{formatEvKwh(totalKwh)}</strong>
          <span>Totalt</span>
        </div>
      </div>
      <ul className="evdash-mix-legend">
        {slices.map((slice) => (
          <li key={slice.id}>
            <span style={{ background: slice.color }} />
            <span>{slice.label}</span>
            <strong>{Math.round(slice.pct)}% · {formatEvKwh(slice.kwh)}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function EvQuickOverviewPanel({
  maxPowerKw,
  avgPowerKw,
  sessions,
  charger,
  bridge,
}: {
  maxPowerKw: number;
  avgPowerKw: number;
  sessions: EvChargingSession[];
  charger: EvCharger;
  bridge: EvBridgeStatus | null;
}) {
  const minutes = totalChargeMinutesToday(sessions);
  const latest = sessions[0];
  return (
    <section className="evdash-panel evdash-quick-panel" data-testid="ev-quick-overview">
      <h2 className="evdash-panel-title">SNABBÖVERSIKT</h2>
      <ul className="evdash-quick-list">
        <li><span>Max effekt idag</span><strong>{maxPowerKw.toFixed(1)} kW</strong></li>
        <li><span>Genomsnitt effekt</span><strong>{avgPowerKw.toFixed(1)} kW</strong></li>
        <li><span>Total laddtid idag</span><strong>{minutes} min</strong></li>
        <li><span>Senaste session</span><strong>{latest ? formatEvSessionTime(latest.started_at) : "—"}</strong></li>
        <li><span>Kabel låst</span><strong>{bridge?.vehicle_connected ? "Ja" : "Nej"}</strong></li>
        <li><span>Jordfelsbrytare</span><strong>{charger.last_charger_error_code ? "Fel" : "OK"}</strong></li>
      </ul>
    </section>
  );
}

export function EvSessionsTable({ sessions }: { sessions: EvChargingSession[] }) {
  return (
    <section className="evdash-panel evdash-sessions-panel" id="ev-sessions" data-testid="ev-sessions-table">
      <h2 className="evdash-panel-title">SENASTE LADDSESSIONER</h2>
      {sessions.length === 0 ? (
        <p className="evdash-muted">Inga sessioner ännu.</p>
      ) : (
        <div className="evdash-table-wrap">
          <table className="evdash-table">
            <thead>
              <tr>
                <th>Start</th>
                <th>Slut</th>
                <th>Varaktighet</th>
                <th>Energi</th>
                <th>Kostnad</th>
                <th>Källa</th>
                <th>Snitt effekt</th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 8).map((session) => {
                const source = sessionSourceLabel(session);
                const avgW = sessionAveragePowerW(session);
                return (
                  <tr key={session.id}>
                    <td>{formatEvSessionTime(session.started_at)}</td>
                    <td>{session.ended_at ? formatEvSessionTime(session.ended_at) : "—"}</td>
                    <td>{formatEvDuration(session.started_at, session.ended_at)}</td>
                    <td>{formatEvKwh(session.total_energy_kwh)}</td>
                    <td>{session.actual_cost_sek != null ? formatSekAmount(session.actual_cost_sek).label : "—"}</td>
                    <td>
                      <span
                        className={`evdash-source-pill evdash-source-${source.tone}`}
                        title={source.detail}
                      >
                        {source.label}
                      </span>
                    </td>
                    <td>{avgW != null ? formatWatts(avgW) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function EvSavingsPanel({ savings, chart }: { savings: EvChargingSavings | null; chart: EvSavingsChartPoint[] }) {
  if (!savings?.has_data) {
    return (
      <section className="evdash-panel evdash-savings-panel" data-testid="ev-savings-panel">
        <h2 className="evdash-panel-title">SMART LADDNING – BESPARINGAR (30 DAGAR)</h2>
        <p className="evdash-muted">Ingen besparingsdata ännu.</p>
      </section>
    );
  }
  const saved = formatSekAmount(savings.savings_sek);
  const actualOre = savings.period_avg_price_kwh != null ? Math.round(savings.period_avg_price_kwh * 100) : null;
  const baselineOre =
    savings.energy_kwh > 0 ? Math.round((savings.baseline_cost_sek / savings.energy_kwh) * 100) : null;
  return (
    <section className="evdash-panel evdash-savings-panel" data-testid="ev-savings-panel">
      <h2 className="evdash-panel-title">SMART LADDNING – BESPARINGAR (30 DAGAR)</h2>
      <div className="evdash-savings-top">
        <div><p>Sparat</p><strong>{saved.label} ({savings.savings_pct.toFixed(0)}%)</strong></div>
        <div><p>Smart laddat</p><strong>{formatEvKwh(savings.energy_kwh)}</strong></div>
        <div><p>Snittpris</p><strong>{actualOre != null ? `${actualOre} öre/kWh` : "—"}</strong><span>vs {baselineOre != null ? `${baselineOre} öre/kWh` : "—"}</span></div>
      </div>
      {chart.length > 1 ? (
        <div className="evdash-savings-chart">
          <ResponsiveContainer width="100%" height={160}>
            <ComposedChart data={chart}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} width={36} />
              <Area type="monotone" dataKey="actual" fill="#4ade80" fillOpacity={0.25} stroke="#4ade80" name="Ackumulerad besparing" />
              <Line type="monotone" dataKey="baseline" stroke="#94a3b8" strokeDasharray="4 4" dot={false} name="Utan smart laddning" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </section>
  );
}

export function EvManualControlPanel({
  siteSlug,
  charger,
  onUpdated,
}: {
  siteSlug: string;
  charger: EvCharger;
  onUpdated: () => void;
}) {
  const [maxCurrent, setMaxCurrent] = useState(charger.max_current_a);
  const [mode, setMode] = useState(charger.charging_mode ?? "SMART_CHARGE");
  const [targetSoc, setTargetSoc] = useState(charger.target_soc_pct ?? 80);
  const [departureTime, setDepartureTime] = useState(charger.departure_time ?? "07:00");
  const [deadlineEnabled, setDeadlineEnabled] = useState(Boolean(charger.deadline_at));
  const [deadlineAt, setDeadlineAt] = useState<string | null>(charger.deadline_at ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const priceOnly = isPriceOnlyMode(mode);

  useEffect(() => {
    setMaxCurrent(charger.max_current_a);
    setMode(charger.charging_mode ?? "SMART_CHARGE");
    setTargetSoc(charger.target_soc_pct ?? 80);
    setDepartureTime(charger.departure_time ?? "07:00");
    setDeadlineEnabled(Boolean(charger.deadline_at));
    setDeadlineAt(charger.deadline_at ?? null);
  }, [
    charger.id,
    charger.max_current_a,
    charger.charging_mode,
    charger.target_soc_pct,
    charger.departure_time,
    charger.deadline_at,
  ]);

  const saveSmartSettings = async () => {
    if (deadlineEnabled && !deadlineAt) {
      setError("Ange datum och tid för klar senast, eller avaktivera deadline.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await controlEvCharger(siteSlug, charger.id, {
        ...(priceOnly
          ? { clear_deadline_at: true }
          : {
              departure_time: departureTime || undefined,
              target_soc_pct: targetSoc,
              ...(deadlineEnabled && deadlineAt
                ? { deadline_at: deadlineAt, clear_deadline_at: false }
                : { clear_deadline_at: true }),
            }),
      });
      setMessage(deadlineEnabled ? "Avresa och deadline sparade." : "Avresa sparad. Deadline avaktiverad.");
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte spara laddinställningar.");
    } finally {
      setBusy(false);
    }
  };

  const applyMode = async (nextMode: string) => {
    setBusy(true);
    setError(null);
    try {
      await controlEvCharger(siteSlug, charger.id, { charging_mode: nextMode });
      setMode(nextMode);
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte uppdatera läge.");
    } finally {
      setBusy(false);
    }
  };

  const handleCurrent = async (delta: number) => {
    const next = Math.min(32, Math.max(6, maxCurrent + delta));
    setBusy(true);
    setError(null);
    try {
      await updateEvCharger(siteSlug, charger.id, { max_current_a: next });
      setMaxCurrent(next);
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte uppdatera ström.");
    } finally {
      setBusy(false);
    }
  };

  const startNow = async () => {
    setBusy(true);
    setError(null);
    try {
      await setEvChargerOverride(siteSlug, charger.id, { hours: 4 });
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte starta laddning.");
    } finally {
      setBusy(false);
    }
  };

  const stopNow = async () => {
    setBusy(true);
    setError(null);
    try {
      await Promise.all([
        setEvChargerOverride(siteSlug, charger.id, { clear: true }).catch(() => undefined),
        controlEvCharger(siteSlug, charger.id, { charging_mode: "PAUSED" }),
      ]);
      setMode("PAUSED");
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte stoppa laddning.");
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
  };

  return (
    <section className="evdash-panel evdash-control-panel" data-testid="ev-manual-control">
      <h2 className="evdash-panel-title">LADDINSTÄLLNINGAR</h2>
      {error ? <p className="evdash-error" role="alert">{error}</p> : null}
      {message ? <p className="evdash-muted">{message}</p> : null}
      <form onSubmit={handleSubmit} className="evdash-control-form">
        {!priceOnly ? (
          <>
            <label className="evdash-control-field">
              <span>Avfärd (HH:MM)</span>
              <input
                type="text"
                inputMode="numeric"
                pattern="\d{2}:\d{2}"
                value={departureTime}
                disabled={busy}
                aria-label="Avfärdstid"
                onChange={(event) => setDepartureTime(event.target.value)}
              />
            </label>
            <label className="evdash-control-field">
              <span>Mål-SoC (%)</span>
              <input
                type="number"
                min={0}
                max={100}
                value={targetSoc}
                disabled={busy}
                aria-label="Mål-SoC procent"
                onChange={(event) => setTargetSoc(Number(event.target.value))}
              />
            </label>
            <label className="evdash-control-checkbox">
              <input
                type="checkbox"
                checked={deadlineEnabled}
                disabled={busy}
                aria-label="Använd deadline klar senast"
                onChange={(event) => {
                  const enabled = event.target.checked;
                  setDeadlineEnabled(enabled);
                  if (!enabled) {
                    setDeadlineAt(null);
                  }
                }}
              />
              <span>Använd deadline (klar senast)</span>
            </label>
            {deadlineEnabled ? (
              <div className="evdash-control-field">
                <span>Klar senast</span>
                <DeadlineInput
                  value={deadlineAt}
                  idPrefix={`ev-deadline-${charger.id}`}
                  disabled={busy}
                  onChange={setDeadlineAt}
                />
              </div>
            ) : (
              <p className="evdash-muted">Deadline är avaktiverad. Smart laddning planerar utan klar senast.</p>
            )}
            <button
              type="button"
              className="evdash-btn-primary"
              disabled={busy}
              onClick={() => void saveSmartSettings()}
            >
              Spara avresa &amp; deadline
            </button>
            <p className="evdash-muted">
              {deadlineEnabled
                ? "Smart laddning prioriterar klar senast när avresa och deadline är satta."
                : "Avresa och mål-SoC sparas utan deadline."}
            </p>
          </>
        ) : (
          <p className="evdash-muted">
            Billigast pris laddar när elpriset är som lägst. Avresa och klar senast används inte i detta läge.
          </p>
        )}

        <h3 className="evdash-control-subtitle">Manuell kontroll</h3>
        <label className="evdash-control-field">
          <span>Max ström (A)</span>
          <div className="evdash-stepper">
            <button type="button" disabled={busy} onClick={() => handleCurrent(-1)} aria-label="Minska ström">−</button>
            <strong>{maxCurrent}</strong>
            <button type="button" disabled={busy} onClick={() => handleCurrent(1)} aria-label="Öka ström">+</button>
          </div>
        </label>
        <label className="evdash-control-field">
          <span>Laddläge</span>
          <select
            value={mode}
            disabled={busy}
            onChange={async (e) => {
              setMode(e.target.value);
              await applyMode(e.target.value);
            }}
          >
            {Object.entries(EV_MODE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <button type="button" className="evdash-btn-secondary" disabled title="Kabel-lås styrs inte via Charge Amps API">
          Lås kabel
        </button>
        <div className="evdash-control-actions">
          <button type="button" className="evdash-btn-primary" disabled={busy} onClick={startNow}>Starta laddning nu</button>
          <button type="button" className="evdash-btn-danger" disabled={busy} onClick={stopNow}>Stoppa laddning</button>
        </div>
        <p className="evdash-muted">Ändringar tillämpas direkt på laddboxen.</p>
      </form>
    </section>
  );
}

export function EvPlaceholderSection({ title, text }: { title: string; text: string }) {
  return (
    <section className="evdash-panel">
      <h2 className="evdash-panel-title">{title}</h2>
      <p className="evdash-muted">{text}</p>
    </section>
  );
}
