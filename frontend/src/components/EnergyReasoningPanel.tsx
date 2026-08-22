"use client";

import { useEffect, useRef, useState } from "react";

import {
  EnergyReasoning,
  controlEvCharger,
  fetchEnergyReasoning,
  formatWatts,
  updateEvCharger,
} from "@/lib/api";
import { formatOrePerKwh } from "@/lib/prices";

function kw(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatWatts(value);
}

function priceTierLabel(tier: string): string {
  if (tier === "green") return "Grönt (billigt)";
  if (tier === "red") return "Rött (dyrt)";
  if (tier === "normal") return "Normalt";
  return "Okänt";
}

function priceTierClass(tier: string): string {
  if (tier === "green") return "reasoning-tier-green";
  if (tier === "red") return "reasoning-tier-red";
  if (tier === "normal") return "reasoning-tier-normal";
  return "reasoning-tier-unknown";
}

type Props = {
  siteSlug: string;
  chargerId: number;
  refreshSeconds: number;
  onSettingsSaved?: () => void;
};

export default function EnergyReasoningPanel({
  siteSlug,
  chargerId,
  refreshSeconds,
  onSettingsSaved,
}: Props) {
  const [data, setData] = useState<EnergyReasoning | null>(null);
  const [chargingActive, setChargingActive] = useState(false);
  const resumeModeRef = useRef("SMART_CHARGE");
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const reasoning = await fetchEnergyReasoning(siteSlug, chargerId);
        if (cancelled) return;
        setData(reasoning);
        setChargingActive(reasoning.charging_active);
        if (reasoning.charging_mode !== "PAUSED") {
          resumeModeRef.current = reasoning.charging_mode;
        }
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Kunde inte ladda energiresonemang");
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

  const saveChargingToggle = async () => {
    setSaving(true);
    setSettingsMessage(null);
    setError(null);
    try {
      if (chargingActive) {
        await updateEvCharger(siteSlug, chargerId, { bridge_enabled: true });
        await controlEvCharger(siteSlug, chargerId, {
          charging_mode: resumeModeRef.current || "SMART_CHARGE",
        });
      } else {
        if (data && data.charging_mode !== "PAUSED") {
          resumeModeRef.current = data.charging_mode;
        }
        await controlEvCharger(siteSlug, chargerId, { charging_mode: "PAUSED" });
      }
      setSettingsMessage(chargingActive ? "Laddning aktiverad." : "Laddning pausad.");
      onSettingsSaved?.();
      const refreshed = await fetchEnergyReasoning(siteSlug, chargerId);
      setData(refreshed);
      setChargingActive(refreshed.charging_active);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara laddningsinställning");
    } finally {
      setSaving(false);
    }
  };

  if (error && !data) {
    return <p className="form-error">{error}</p>;
  }

  if (!data) {
    return <p>Laddar energiresonemang…</p>;
  }

  return (
    <section className="card diagnostics-panel" data-testid="energy-reasoning-panel">
      <h3>Energifördelning &amp; resonemang</h3>
      <p className="muted">
        Visar Heartbeat-indata och hur EMIC tolkar dem för smart laddning.
      </p>

      <div className="diagnostics-settings" data-testid="energy-reasoning-settings">
        <label className="form-field">
          <span>Laddning aktiv</span>
          <select
            value={chargingActive ? "true" : "false"}
            onChange={(e) => setChargingActive(e.target.value === "true")}
          >
            <option value="true">Ja</option>
            <option value="false">Nej (pausad)</option>
          </select>
        </label>
        <button type="button" className="btn-secondary" disabled={saving} onClick={saveChargingToggle}>
          Spara laddningsläge
        </button>
        {settingsMessage && <p className="form-success">{settingsMessage}</p>}
      </div>

      <div className="reasoning-summary">
        <p>
          Status: <strong>{data.display_status_sv ?? "—"}</strong>
          {data.decision_reason && <span className="muted"> ({data.decision_reason})</span>}
        </p>
        <p>
          Elprisnivå:{" "}
          <span className={`reasoning-tier ${priceTierClass(data.price_tier)}`}>
            {priceTierLabel(data.price_tier)}
          </span>
          {data.current_price_eur_kwh != null && (
            <span className="muted"> — nu {formatOrePerKwh(data.current_price_eur_kwh)}</span>
          )}
        </p>
      </div>

      <div className="diagnostics-grid">
        <div>
          <h4>Heartbeat (indata)</h4>
          <ul>
            <li>EMS-läge: {data.heartbeat_charging_mode ?? "—"}</li>
            <li>PV: {kw(data.pv_power_w)}</li>
            <li>Huslast: {kw(data.home_consumption_w)}</li>
            <li>Nät in: {kw(data.grid_import_w)}</li>
            <li>Nät ut: {kw(data.grid_export_w)}</li>
            <li>Batteri SOC: {data.battery_soc_pct ?? "—"}%</li>
            <li>EV (HB): {kw(data.ev_actual_power_w)}</li>
            <li>EV-mål: {kw(data.ev_target_power_w)}</li>
            <li>Nät-laddning rekommenderad: {data.ev_charge_from_grid_recommended ? "Ja" : "Nej"}</li>
          </ul>
        </div>

        <div>
          <h4>EMIC (beslut)</h4>
          <ul>
            <li>Bridge: {data.bridge_enabled ? "På" : "Av"}</li>
            <li>Läge: {data.charging_mode}</li>
            <li>State: {data.smart_charging_state ?? "—"}</li>
            <li>Bil inkopplad: {data.vehicle_connected == null ? "—" : data.vehicle_connected ? "Ja" : "Nej"}</li>
            <li>Halo online: {data.halo_connected == null ? "—" : data.halo_connected ? "Ja" : "Nej"}</li>
            <li>Begärd ström: {data.requested_current_a ?? "—"} A</li>
            <li>Tillämpad ström: {data.applied_current_a ?? "—"} A</li>
            <li>Prisregel: {data.price_would_charge ? "Ladda" : "Vänta"} ({data.price_reason})</li>
          </ul>
        </div>
      </div>

      {data.energy_flow_line && (
        <p>
          <strong>Energiflöde:</strong> {data.energy_flow_line}
          {data.energy_balance_status && (
            <span className="muted"> — balans {data.energy_balance_status}</span>
          )}
        </p>
      )}

      {data.active_optimizations.length > 0 && (
        <p>
          <strong>Heartbeat AI:</strong> {data.active_optimizations.join(", ")}
        </p>
      )}

      {data.solar_plan_available && (
        <p>
          <strong>Solplan:</strong> {data.solar_plan_reason ?? "—"}
          {data.solar_planned_grid_kwh != null && ` (${data.solar_planned_grid_kwh.toFixed(1)} kWh nät)`}
        </p>
      )}

      <div>
        <h4>Resonemang steg för steg</h4>
        <ol className="reasoning-steps" data-testid="reasoning-steps">
          {data.reasoning_steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
