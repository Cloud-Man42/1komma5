"use client";

import { useCallback, useEffect, useState } from "react";

import {
  SpaEnergyPeriod,
  SpaHealth,
  SpaStatus,
  fetchSpaEnergyPeriod,
  fetchSpaHealth,
  fetchSpaStatus,
  formatWatts,
} from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

import { SpaEnergyAnalysis } from "@/components/SpaEnergyAnalysis";
import { SpaEnergyBreakdown } from "@/components/SpaEnergyBreakdown";
import { SpaEnergyHistory } from "@/components/SpaEnergyHistory";
import { SpaHealthPanel } from "@/components/SpaHealthPanel";

const PERIOD_TABS = [
  { id: "today", label: "Idag" },
  { id: "week", label: "Vecka" },
  { id: "month", label: "Månad" },
  { id: "year", label: "År" },
  { id: "total", label: "Totalt" },
] as const;

function formatTemp(value: number | null): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} °C`;
}

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} kWh`;
}

export function ArcticSpaPanel({ siteSlug }: { siteSlug: string }) {
  const [status, setStatus] = useState<SpaStatus | null>(null);
  const [today, setToday] = useState<SpaEnergyPeriod | null>(null);
  const [health, setHealth] = useState<SpaHealth | null>(null);
  const [period, setPeriod] = useState<string>("today");
  const [error, setError] = useState<string | null>(null);
  const refreshSeconds = useDashboardRefreshSeconds();

  const load = useCallback(async () => {
    try {
      const [spaStatus, spaToday, spaHealth] = await Promise.all([
        fetchSpaStatus(siteSlug),
        fetchSpaEnergyPeriod(siteSlug, "today"),
        fetchSpaHealth(siteSlug),
      ]);
      setStatus(spaStatus);
      setToday(spaToday);
      setHealth(spaHealth);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda Arctic Spa");
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), refreshSeconds * 1000);
    return () => clearInterval(timer);
  }, [load, refreshSeconds]);

  if (error && !status) {
    return <p className="form-error">{error}</p>;
  }

  if (!status) {
    return <p className="muted">Laddar Arctic Spa…</p>;
  }

  if (!status.integration_enabled) {
    return (
      <section className="card diagnostics-panel" data-testid="arctic-spa-panel">
        <h3>Arctic Spa</h3>
        <p className="muted">Integrationen är inte aktiverad. Konfigurera under Konfiguration → Anläggningar.</p>
      </section>
    );
  }

  return (
    <section className="card diagnostics-panel" data-testid="arctic-spa-panel">
      <h3>Arctic Spa</h3>

      <div className="spa-kpi-grid">
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatTemp(status.water_temperature_c)}</p>
          <p className="spa-kpi-label">Aktuell temperatur</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatTemp(status.set_temperature_c)}</p>
          <p className="spa-kpi-label">Måltemperatur</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatWatts(status.current_power_w ?? 0)}</p>
          <p className="spa-kpi-label">Aktuell effekt</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{today?.has_data ? formatKwh(today.energy_kwh) : "Väntar på mätdata"}</p>
          <p className="spa-kpi-label">Förbrukning idag</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {today?.has_data ? formatSekAmount(today.actual_cost_sek).label : "—"}
          </p>
          <p className="spa-kpi-label">Kostnad idag</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {today?.own_energy_pct != null ? `${today.own_energy_pct.toFixed(0)} %` : "—"}
          </p>
          <p className="spa-kpi-label">Egen energi</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {today?.savings_sek != null ? formatSekAmount(today.savings_sek).label : "—"}
          </p>
          <p className="spa-kpi-label">Besparing idag</p>
        </div>
      </div>

      <p className="spa-status-line">
        Värmare: <strong>{status.heater_active ? "Aktiv" : "Inaktiv"}</strong>
        {" · "}
        {status.pump_label}
        {" · "}
        Spa: <strong>{status.online ? "Online" : "Offline"}</strong>
        {" · "}
        Kvalitet: {status.data_quality}
      </p>

      <div className="spa-tabs">
        {PERIOD_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={period === tab.id ? "spa-tab active" : "spa-tab"}
            onClick={() => setPeriod(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <SpaEnergyHistory siteSlug={siteSlug} period={period} />
      <SpaEnergyBreakdown siteSlug={siteSlug} period={period} />
      <SpaEnergyAnalysis siteSlug={siteSlug} period={period} />
      {health && <SpaHealthPanel health={health} />}
      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
