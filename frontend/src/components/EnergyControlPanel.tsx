"use client";

import { useCallback, useEffect, useState } from "react";
import type { EnergyControlStatus } from "@/lib/api";
import {
  fetchEnergyControlRecent,
  fetchEnergyControlStatus,
  updateEnergyControlSettings,
} from "@/lib/api";

const MODES = [
  { value: "MONITOR_ONLY", label: "Monitor only" },
  { value: "RECOMMEND", label: "Recommend" },
  { value: "SEMI_AUTOMATIC", label: "Semi-automatic" },
  { value: "AUTOMATIC", label: "Automatic" },
] as const;

function modeLabel(mode: string): string {
  return MODES.find((m) => m.value === mode)?.label ?? mode;
}

export function EnergyControlPanel({ siteSlug }: { siteSlug: string }) {
  const [status, setStatus] = useState<EnergyControlStatus | null>(null);
  const [recentCount, setRecentCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextStatus, recent] = await Promise.all([
        fetchEnergyControlStatus(siteSlug),
        fetchEnergyControlRecent(siteSlug, 5),
      ]);
      setStatus(nextStatus);
      setRecentCount(recent.actions.length);
      setError(null);
    } catch (err) {
      setStatus(null);
      setError(err instanceof Error ? err.message : "Failed to load control status");
    } finally {
      setLoading(false);
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleModeChange(mode: string) {
    if (!status || saving) return;
    setSaving(true);
    try {
      const next = await updateEnergyControlSettings(siteSlug, { optimization_mode: mode });
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update mode");
    } finally {
      setSaving(false);
    }
  }

  async function handleControlToggle(enabled: boolean) {
    if (!status || saving) return;
    setSaving(true);
    try {
      const next = await updateEnergyControlSettings(siteSlug, { control_enabled: enabled });
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update control flag");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card" data-testid="energy-control-panel">
      <h3>Energistyrning</h3>
      {loading ? (
        <p className="muted">Laddar styrningsläge…</p>
      ) : error ? (
        <p className="muted">Kunde inte hämta styrningsstatus.</p>
      ) : status ? (
        <>
          <div className="energy-control-grid">
            <div>
              <p className="energy-control-label">Optimeringsläge</p>
              <select
                className="energy-control-select"
                value={status.optimization_mode}
                disabled={saving}
                onChange={(event) => void handleModeChange(event.target.value)}
              >
                {MODES.map((mode) => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
              <p className="muted">Aktivt: {modeLabel(status.optimization_mode)}</p>
            </div>
            <div>
              <p className="energy-control-label">Kontroll aktiverad</p>
              <label className="energy-control-toggle">
                <input
                  type="checkbox"
                  checked={status.control_enabled}
                  disabled={saving}
                  onChange={(event) => void handleControlToggle(event.target.checked)}
                />
                <span>{status.control_enabled ? "På" : "Av"}</span>
              </label>
              <p className="muted">
                {status.writes_allowed
                  ? "Manuell applicering tillåten."
                  : "Endast monitorering/rekommendation."}
              </p>
            </div>
          </div>
          <dl className="energy-control-meta">
            <div>
              <dt>Provider</dt>
              <dd>{status.provider}</dd>
            </div>
            <div>
              <dt>Automatik</dt>
              <dd>{status.automatic_allowed ? "Tillåten" : "Blockerad"}</dd>
            </div>
            <div>
              <dt>Senaste händelse</dt>
              <dd>
                {status.last_action
                  ? `${status.last_action.action} · ${status.last_action.outcome}`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt>Loggade åtgärder</dt>
              <dd>{recentCount}</dd>
            </div>
          </dl>
          <p className="muted energy-control-note">
            Heartbeat-provider är aktiv i produktion. RECOMMEND loggar rekommendationer utan skrivningar tills kontroll
            aktiveras explicit.
          </p>
        </>
      ) : null}
    </section>
  );
}
