"use client";

import { useEffect, useState } from "react";

import {
  EnergyBalanceSnapshot,
  SiteEnergyConfig,
  VirtualEvseStatus,
  fetchEnergyBalance,
  fetchSiteEnergyConfig,
  fetchVirtualEvseStatus,
  formatWatts,
  updateEvCharger,
  updateSiteEnergyConfig,
} from "@/lib/api";

function kw(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatWatts(value);
}

function statusBadge(status: string | null | undefined): string {
  if (!status || status === "OK" || status === "UNAVAILABLE") return "";
  return status;
}

function loadIncludesValue(config: SiteEnergyConfig | null): string {
  if (!config || config.load_includes_ev_charger === null) return "unknown";
  return config.load_includes_ev_charger ? "true" : "false";
}

type Props = {
  siteSlug: string;
  chargerId: number;
  refreshSeconds: number;
  virtualEvseEnabled?: boolean;
  onSettingsSaved?: () => void;
};

export default function VirtualEvseDiagnosticsPanel({
  siteSlug,
  chargerId,
  refreshSeconds,
  virtualEvseEnabled = false,
  onSettingsSaved,
}: Props) {
  const [balance, setBalance] = useState<EnergyBalanceSnapshot | null>(null);
  const [virtualEvse, setVirtualEvse] = useState<VirtualEvseStatus | null>(null);
  const [siteConfig, setSiteConfig] = useState<SiteEnergyConfig | null>(null);
  const [evseEnabled, setEvseEnabled] = useState(virtualEvseEnabled);
  const [loadIncludes, setLoadIncludes] = useState("unknown");
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEvseEnabled(virtualEvseEnabled);
  }, [virtualEvseEnabled]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [balanceData, evseData, configData] = await Promise.all([
          fetchEnergyBalance(siteSlug, chargerId),
          fetchVirtualEvseStatus(siteSlug, chargerId),
          fetchSiteEnergyConfig(siteSlug),
        ]);
        if (!cancelled) {
          setBalance(balanceData);
          setVirtualEvse(evseData);
          setSiteConfig(configData);
          setLoadIncludes(loadIncludesValue(configData));
          setEvseEnabled(evseData.virtual_evse_enabled);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Kunde inte ladda diagnostik");
        }
      }
    }

    load();
    const timer = setInterval(load, Math.max(refreshSeconds, 15) * 1000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [siteSlug, chargerId, refreshSeconds]);

  const saveSettings = async () => {
    setSaving(true);
    setSettingsMessage(null);
    setError(null);
    try {
      await updateEvCharger(siteSlug, chargerId, { virtual_evse_enabled: evseEnabled });
      const payload =
        loadIncludes === "unknown"
          ? { clear_load_includes_ev_charger: true }
          : { load_includes_ev_charger: loadIncludes === "true" };
      await updateSiteEnergyConfig(siteSlug, payload);
      setSettingsMessage("Inställningar sparade.");
      onSettingsSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara inställningar");
    } finally {
      setSaving(false);
    }
  };

  if (error && !balance) {
    return <p className="form-error">{error}</p>;
  }

  if (!balance || !virtualEvse) {
    return <p>Laddar energidiagnostik…</p>;
  }

  const badge = statusBadge(balance.status);

  return (
    <section className="card diagnostics-panel" data-testid="virtual-evse-diagnostics">
      <h3>Virtual EVSE &amp; energibalans</h3>

      <div className="diagnostics-settings" data-testid="virtual-evse-settings">
        <label className="form-field">
          <span>Virtual EVSE aktiv</span>
          <select
            value={evseEnabled ? "true" : "false"}
            onChange={(e) => setEvseEnabled(e.target.value === "true")}
          >
            <option value="false">Nej</option>
            <option value="true">Ja</option>
          </select>
        </label>
        <label className="form-field">
          <span>HB huslast inkluderar EV-laddare</span>
          <select value={loadIncludes} onChange={(e) => setLoadIncludes(e.target.value)}>
            <option value="unknown">Okänt</option>
            <option value="true">Ja</option>
            <option value="false">Nej</option>
          </select>
        </label>
        <button type="button" className="btn-secondary" disabled={saving} onClick={saveSettings}>
          Spara diagnostikinställningar
        </button>
        {settingsMessage && <p className="form-success">{settingsMessage}</p>}
      </div>

      {badge && (
        <p className="status-badge" data-testid="balance-status-badge">
          {badge}
        </p>
      )}

      <div className="diagnostics-grid">
        <div>
          <h4>Physical Energy System</h4>
          <p>Inverter: {balance.inverter_display_name || siteConfig?.inverter_display_name}</p>
          <ul>
            <li>PV: {kw(balance.sungrow_pv_power_w)}</li>
            <li>House load: {kw(balance.sungrow_load_power_w)}</li>
            <li>Battery SOC: {balance.sungrow_battery_soc_pct ?? "—"}%</li>
            <li>Grid import: {kw(balance.sungrow_grid_import_w)}</li>
            <li>Grid export: {kw(balance.sungrow_grid_export_w)}</li>
          </ul>
        </div>

        <div>
          <h4>EV Charger</h4>
          <p>
            {virtualEvse.physical_charger_label}, {virtualEvse.ev_vehicle_label}
          </p>
          <p>Charging: {kw(balance.halo_power_w)}</p>
          <p>Non-EV load: {kw(balance.non_ev_house_load_w)}</p>
          {balance.non_ev_house_load_reason && balance.non_ev_house_load_w == null && (
            <p className="muted">{balance.non_ev_house_load_reason}</p>
          )}
        </div>

        <div>
          <h4>Virtual EVSE</h4>
          <p>SEMP device: {virtualEvse.semp_device_id ?? "—"}</p>
          <p>SEMP state: {virtualEvse.status ?? "—"}</p>
          <p>Reported: {kw(virtualEvse.reported_power_w)}</p>
          <p>Halo: {kw(virtualEvse.halo_power_w)}</p>
          <p>Heartbeat detected: {virtualEvse.heartbeat_detected ? "YES" : "NO"}</p>
        </div>
      </div>

      <div>
        <h4>Energy Flow Diagnostics</h4>
        <p>{balance.energy_flow_line ?? "—"}</p>
        {balance.residual_w != null && <p>Residual: {kw(balance.residual_w)}</p>}
      </div>

      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
