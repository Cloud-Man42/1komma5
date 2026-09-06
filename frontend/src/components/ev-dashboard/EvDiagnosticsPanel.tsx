"use client";

import { useEffect, useState } from "react";
import {
  type EnergyBalanceSnapshot,
  type EnergyReasoning,
  type EvBridgeStatus,
  fetchEnergyBalance,
  formatWatts,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

function kw(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatWatts(value);
}

type Props = {
  siteSlug: string;
  chargerId: number;
  bridge: EvBridgeStatus | null;
  reasoning: EnergyReasoning | null;
  refreshSeconds: number;
};

export function EvDiagnosticsPanel({
  siteSlug,
  chargerId,
  bridge,
  reasoning,
  refreshSeconds,
}: Props) {
  const [balance, setBalance] = useState<EnergyBalanceSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const snapshot = await fetchEnergyBalance(siteSlug, chargerId);
        if (!cancelled) {
          setBalance(snapshot);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Kunde inte ladda energibalans");
        }
      }
    }

    void load();
    const timer = setInterval(load, Math.max(refreshSeconds, 15) * 1000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [siteSlug, chargerId, refreshSeconds]);

  if (error && !balance) {
    return (
      <section className="evdash-panel diagnostics-panel" data-testid="ev-diagnostics-panel">
        <p className="evdash-error" role="alert">{error}</p>
      </section>
    );
  }

  if (!balance) {
    return (
      <section className="evdash-panel diagnostics-panel" data-testid="ev-diagnostics-panel">
        <p className="evdash-muted">Laddar diagnostik…</p>
      </section>
    );
  }

  const bridgeStale = bridge?.stale ?? false;
  const balanceStatus = balance.status && balance.status !== "OK" ? balance.status : null;

  return (
    <section className="evdash-panel diagnostics-panel" data-testid="ev-diagnostics-panel">
      <h2 className="evdash-panel-title">BRIDGE &amp; ENERGIBALANS</h2>

      <div className="diagnostics-grid">
        <div>
          <h3>Virtual EV bridge</h3>
          <ul className="evdash-spec-list">
            <li>Bridge: {bridge?.bridge_enabled ? "Aktiv" : "Av"}</li>
            <li>Policy: {bridge?.active_policy ?? "—"}</li>
            <li>Halo: {bridge?.halo_connected ? "Online" : "Offline"}</li>
            <li>Bil: {bridge?.vehicle_connected ? "Inkoppad" : "Ej inkopplad"}</li>
            <li>Ström begärd/tillämpad: {bridge?.requested_current_a ?? "—"} / {bridge?.applied_current_a ?? "—"} A</li>
            <li>Senaste bridge-körning: {bridge?.last_bridge_run_at ? formatRelativeTime(bridge.last_bridge_run_at) : "—"}</li>
            <li>Heartbeat-data: {bridge?.last_heartbeat_data_at ? formatRelativeTime(bridge.last_heartbeat_data_at) : "—"}</li>
            <li>Uplink: {bridgeStale ? "Stale" : "OK"}</li>
          </ul>
          {bridge?.decision_reason ? <p className="evdash-muted">{bridge.decision_reason}</p> : null}
        </div>

        <div>
          <h3>Energibalans</h3>
          {balanceStatus ? (
            <p className="status-badge" data-testid="ev-balance-status-badge">
              {balanceStatus}
            </p>
          ) : null}
          <ul className="evdash-spec-list">
            <li>PV: {kw(balance.sungrow_pv_power_w)}</li>
            <li>Huslast: {kw(balance.sungrow_load_power_w)}</li>
            <li>Batteri SOC: {balance.sungrow_battery_soc_pct ?? "—"}%</li>
            <li>Nätimport/export: {kw(balance.sungrow_grid_import_w)} / {kw(balance.sungrow_grid_export_w)}</li>
            <li>Halo laddning: {kw(balance.halo_power_w)}</li>
            <li>Icke-EV last: {kw(balance.non_ev_house_load_w)}</li>
            {balance.residual_w != null ? <li>Residual: {kw(balance.residual_w)}</li> : null}
          </ul>
          {balance.non_ev_house_load_reason && balance.non_ev_house_load_w == null ? (
            <p className="evdash-muted">{balance.non_ev_house_load_reason}</p>
          ) : null}
        </div>

        <div>
          <h3>Resonemang</h3>
          <p>Status: {reasoning?.display_status_sv ?? bridge?.display_status_sv ?? "—"}</p>
          <p>Energiflöde: {balance.energy_flow_line ?? reasoning?.energy_flow_line ?? "—"}</p>
          <p>Balansstatus: {reasoning?.energy_balance_status ?? balance.status ?? "—"}</p>
          {reasoning?.reasoning_steps?.length ? (
            <ol className="evdash-reasoning-steps">
              {reasoning.reasoning_steps.map((step, index) => (
                <li key={`${step}-${index}`}>{step}</li>
              ))}
            </ol>
          ) : (
            <p className="evdash-muted">Inga resonemangssteg tillgängliga.</p>
          )}
        </div>
      </div>

      {error ? <p className="evdash-error" role="alert">{error}</p> : null}
    </section>
  );
}
