"use client";

import { useEffect, useState } from "react";
import { SolarSiteConfig, fetchSolarConfig, updateSolarConfig } from "@/lib/api";

interface SolarSiteConfigPanelProps {
  siteSlug: string;
}

export function SolarSiteConfigPanel({ siteSlug }: SolarSiteConfigPanelProps) {
  const [config, setConfig] = useState<SolarSiteConfig | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSolarConfig(siteSlug)
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda solprofil"));
  }, [siteSlug]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateSolarConfig(siteSlug, {
        latitude: config.latitude,
        longitude: config.longitude,
        installed_peak_power_kw: config.installed_peak_power_kw,
        azimuth_deg: config.azimuth_deg,
        tilt_deg: config.tilt_deg,
        inverter_max_power_kw: config.inverter_max_power_kw,
        system_loss_percent: config.system_loss_percent,
        enabled: config.enabled,
        tilt_estimated: config.tilt_estimated,
        azimuth_estimated: config.azimuth_estimated,
      });
      setConfig(updated);
      setMessage("Solprofil sparad.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara");
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <p className="muted">Laddar solprofil…</p>;

  const needsSetup = !config.complete;

  return (
    <details
      id={`solar-${siteSlug}`}
      className="bridge-settings solar-site-config"
      open={needsSetup || config.enabled}
    >
      <summary>Solprognos — plats &amp; anläggning</summary>
      <p className="muted">
        Ange anläggningens koordinater (hitta dem t.ex. via Google Maps → högerklicka på platsen →
        koordinater). Krävs för väderdata och solelprognos.
      </p>
      <div className="config-form">
        <div className="form-grid">
          <label className="form-field">
            <span>Latitud (°)</span>
            <input
              type="number"
              step="0.0001"
              placeholder="t.ex. 55.6050"
              value={config.latitude ?? ""}
              onChange={(e) =>
                setConfig({ ...config, latitude: e.target.value ? Number(e.target.value) : null })
              }
            />
          </label>
          <label className="form-field">
            <span>Longitud (°)</span>
            <input
              type="number"
              step="0.0001"
              placeholder="t.ex. 13.0038"
              value={config.longitude ?? ""}
              onChange={(e) =>
                setConfig({ ...config, longitude: e.target.value ? Number(e.target.value) : null })
              }
            />
          </label>
          <label className="form-field">
            <span>Installerad effekt (kWp)</span>
            <input
              type="number"
              step="0.1"
              placeholder="t.ex. 8.0"
              value={config.installed_peak_power_kw ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  installed_peak_power_kw: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </label>
          <label className="form-field">
            <span>Azimut (° syd=180)</span>
            <input
              type="number"
              placeholder="180"
              value={config.azimuth_deg ?? ""}
              onChange={(e) =>
                setConfig({ ...config, azimuth_deg: e.target.value ? Number(e.target.value) : null })
              }
            />
          </label>
          <label className="form-field">
            <span>Lutning (°)</span>
            <input
              type="number"
              placeholder="30"
              value={config.tilt_deg ?? ""}
              onChange={(e) =>
                setConfig({ ...config, tilt_deg: e.target.value ? Number(e.target.value) : null })
              }
            />
          </label>
          <label className="form-field">
            <span>Växelriktare max (kW)</span>
            <input
              type="number"
              step="0.1"
              value={config.inverter_max_power_kw ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  inverter_max_power_kw: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </label>
          <label className="form-field">
            <span>Systemförlust (%)</span>
            <input
              type="number"
              step="0.1"
              value={config.system_loss_percent}
              onChange={(e) =>
                setConfig({ ...config, system_loss_percent: Number(e.target.value) })
              }
            />
          </label>
        </div>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
          />
          Aktivera solprognos
        </label>
        {config.enabled &&
          (config.latitude == null ||
            config.longitude == null ||
            config.installed_peak_power_kw == null ||
            config.installed_peak_power_kw <= 0) && (
            <p className="form-error">Fyll i latitud, longitud och kWp innan aktivering.</p>
          )}
        {needsSetup && !config.enabled && (
          <p className="muted">Tips: fyll i koordinater och kWp, spara, och aktivera sedan prognosen.</p>
        )}
        <button
          type="button"
          className="btn-secondary"
          disabled={saving}
          onClick={() => void handleSave()}
        >
          {saving ? "Sparar…" : "Spara solprofil"}
        </button>
        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}
      </div>
    </details>
  );
}
