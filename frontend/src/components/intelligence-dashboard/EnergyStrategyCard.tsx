"use client";

import { useEffect, useState } from "react";
import type { EnergyStrategyCurrent } from "@/lib/api";
import { fetchEnergyStrategyCurrent } from "@/lib/api";
import { toOrePerKwh } from "@/lib/prices";

function formatOre(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(toOrePerKwh(value))} öre`;
}

function formatTime(iso: string | null | undefined, timezone: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

function strategyLabel(state: string): string {
  switch (state) {
    case "PEAK_AHEAD":
      return "SPARA ENERGI";
    case "SAVE_BATTERY":
      return "SPARA BATTERI";
    case "CHARGE_BATTERY":
      return "LADDA BATTERI";
    case "DISCHARGE_BATTERY":
      return "URLADDA BATTERI";
    case "EXPORT":
      return "EXPORTERA";
    case "CHARGE_VEHICLE":
      return "LADDA FORDON";
    case "PEAK_PROTECTION":
      return "TOPPSKYDD";
    default:
      return "NORMAL DRIFT";
  }
}

export function EnergyStrategyCard({ slug, timezone }: { slug: string; timezone: string }) {
  const [data, setData] = useState<EnergyStrategyCurrent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchEnergyStrategyCurrent(slug)
        .then((payload) => {
          if (active) {
            setData(payload);
            setError(null);
          }
        })
        .catch((err: Error) => {
          if (active) {
            setData(null);
            setError(err.message);
          }
        });
    load();
    const interval = setInterval(load, 120_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug]);

  if (error && !data) {
    return (
      <section className="idash-strategy-card" data-testid="energy-strategy-card">
        <header className="idash-strategy-header">
          <h2>EMIC ENERGY STRATEGY</h2>
        </header>
        <p className="idash-strategy-empty">Strategidata otillgänglig.</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="idash-strategy-card" data-testid="energy-strategy-card">
        <header className="idash-strategy-header">
          <h2>EMIC ENERGY STRATEGY</h2>
        </header>
        <p className="idash-strategy-empty">Hämtar strategidata…</p>
      </section>
    );
  }

  const nowLabel = formatTime(data.period_start, timezone);

  return (
    <section className="idash-strategy-card" data-testid="energy-strategy-card">
      <header className="idash-strategy-header">
        <div>
          <h2>EMIC ENERGY STRATEGY</h2>
          <p className="idash-strategy-mode">{data.optimization_mode.replaceAll("_", " ")}</p>
        </div>
        <div className="idash-strategy-now">
          <span>NU</span>
          <strong>{nowLabel}</strong>
        </div>
      </header>

      <div className="idash-strategy-prices">
        <div>
          <span className="idash-strategy-label">Nord Pool</span>
          <strong>{formatOre(data.market_price_sek_kwh)}</strong>
        </div>
        <div>
          <span className="idash-strategy-label">Faktiskt köp</span>
          <strong>{formatOre(data.import_price_sek_kwh)}</strong>
        </div>
        <div>
          <span className="idash-strategy-label">Faktisk försäljning</span>
          <strong>{formatOre(data.export_price_sek_kwh)}</strong>
        </div>
      </div>

      {data.grid_surcharge_sek_kwh != null ? (
        <p className="idash-strategy-tariff" data-testid="strategy-grid-surcharge">
          Nätavgift: <strong>{formatOre(data.grid_surcharge_sek_kwh)}</strong>
        </p>
      ) : null}

      {data.strategy_state === "PEAK_PROTECTION" && data.fuse_utilization_pct != null ? (
        <p className="idash-strategy-peak-banner" data-testid="strategy-peak-banner">
          Huvudsäkring ~{Math.round(data.fuse_utilization_pct)}% utnyttjad
          {data.fuse_headroom_a != null ? ` · ${data.fuse_headroom_a.toFixed(1)} A kvar` : null}
        </p>
      ) : null}

      <div className="idash-strategy-body">
        <div className="idash-strategy-state">
          <span className="idash-strategy-dot" aria-hidden="true" />
          <strong>{strategyLabel(data.strategy_state)}</strong>
        </div>

        <div className="idash-strategy-metrics">
          <div>
            <span>Batteri</span>
            <strong>{data.battery_soc_pct != null ? `${Math.round(data.battery_soc_pct)} %` : "—"}</strong>
          </div>
          <div>
            <span>Nästa pristopp</span>
            <strong>{formatTime(data.next_peak_at, timezone)}</strong>
          </div>
          <div>
            <span>Förväntat köp då</span>
            <strong>{formatOre(data.next_peak_import_sek_kwh)}</strong>
          </div>
          <div>
            <span>Rekomm. reserv</span>
            <strong>
              {data.recommended_reserve_soc_pct != null
                ? `${Math.round(data.recommended_reserve_soc_pct)} %`
                : "—"}
            </strong>
          </div>
        </div>

        {data.ev_recommendations.length > 0 ? (
          <ul className="idash-strategy-ev-list" data-testid="strategy-ev-recommendations">
            {data.ev_recommendations.map((rec) => (
              <li key={rec.charger_id}>
                <strong>{rec.charger_name}</strong>: {formatTime(rec.window_start, timezone)}–
                {formatTime(rec.window_end, timezone)} · ~{formatOre(rec.avg_import_sek_kwh)}
                {rec.estimated_saving_sek != null ? ` · sparar ~${rec.estimated_saving_sek.toFixed(2)} kr` : null}
              </li>
            ))}
          </ul>
        ) : null}

        {data.expected_saving_today_sek != null ? (
          <p className="idash-strategy-saving">
            Uppskattad besparing idag: <strong>{data.expected_saving_today_sek.toFixed(2)} SEK</strong>
          </p>
        ) : null}

        <p className="idash-strategy-reason">{data.reason_sv || data.reason}</p>
        <p className="idash-strategy-quality">
          Kvalitet: {data.import_quality} · Konfidens {Math.round(data.confidence * 100)} %
          {data.recommended_action ? ` · EOV: ${data.recommended_action.replaceAll("_", " ")}` : null}
        </p>
      </div>
    </section>
  );
}
