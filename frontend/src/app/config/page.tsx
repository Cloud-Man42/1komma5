"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { SitesManager } from "@/components/SitesManager";
import { AppleDevicesAdminPanel } from "@/components/AppleDevicesAdminPanel";
import {
  ChargeAmpsConfig,
  ChargingReadiness,
  HeartbeatConfig,
  HeartbeatConfigUpdate,
  fetchChargeAmpsConfig,
  fetchChargingReadiness,
  fetchHeartbeatConfig,
  saveHeartbeatConfig,
} from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  mock: "Mock — syntetisk data",
  not_configured: "Ej konfigurerad",
  configured: "Konfigurerad",
  unknown: "Okänd",
};

const CLOUD_HOST = "heartbeat.1komma5grad.com";

type FormState = {
  connection_type: "mock" | "cloud" | "local";
  host: string;
  port: number;
  use_tls: boolean;
  api_path: string;
  poll_interval_seconds: number;
  dashboard_refresh_seconds: number;
  username: string;
  password: string;
  api_token: string;
};

function configToForm(config: HeartbeatConfig): FormState {
  return {
    connection_type: config.connection_type,
    host: config.connection_type === "cloud" ? CLOUD_HOST : config.host,
    port: config.port,
    use_tls: config.use_tls,
    api_path: config.api_path,
    poll_interval_seconds: config.poll_interval_seconds,
    dashboard_refresh_seconds: config.dashboard_refresh_seconds,
    username: config.username,
    password: "",
    api_token: "",
  };
}

export default function ConfigPage() {
  const [config, setConfig] = useState<HeartbeatConfig | null>(null);
  const [chargeAmps, setChargeAmps] = useState<ChargeAmpsConfig | null>(null);
  const [readiness, setReadiness] = useState<ChargingReadiness | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    Promise.all([fetchHeartbeatConfig(), fetchChargeAmpsConfig(), fetchChargingReadiness()])
      .then(([heartbeat, chargeamps, ready]) => {
        setConfig(heartbeat);
        setForm(configToForm(heartbeat));
        setChargeAmps(chargeamps);
        setReadiness(ready);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda konfiguration"));
  }, []);

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  };

  const handleConnectionTypeChange = (value: "mock" | "cloud" | "local") => {
    if (!form) return;
    const next = { ...form, connection_type: value };
    if (value === "cloud") {
      next.host = CLOUD_HOST;
      next.port = 443;
      next.use_tls = true;
      next.api_path = "/api";
    } else if (value === "local" && form.host === CLOUD_HOST) {
      next.host = "";
      next.port = 8080;
      next.use_tls = false;
    }
    setForm(next);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form || !config) return;

    setSaving(true);
    setSaveMessage(null);
    setError(null);

    const payload: HeartbeatConfigUpdate = {
      connection_type: form.connection_type,
      host: form.connection_type === "cloud" ? CLOUD_HOST : form.host.trim(),
      port: form.port,
      use_tls: form.use_tls,
      api_path: form.api_path,
      poll_interval_seconds: form.poll_interval_seconds,
      dashboard_refresh_seconds: form.dashboard_refresh_seconds,
      username: form.username.trim(),
      sites: [],
    };

    if (form.password.trim()) payload.password = form.password;
    if (form.api_token.trim()) payload.api_token = form.api_token;

    try {
      const saved = await saveHeartbeatConfig(payload);
      setConfig(saved);
      setForm(configToForm(saved));
      setSaveMessage("Konfiguration sparad.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara konfiguration");
    } finally {
      setSaving(false);
    }
  };

  if (error && !form) {
    return (
      <section>
        <Link href="/" className="back-link">← Dashboard</Link>
        <p className="muted">Fel: {error}</p>
      </section>
    );
  }

  if (!form || !config) {
    return (
      <section>
        <Link href="/" className="back-link">← Dashboard</Link>
        <p className="muted">Laddar konfiguration…</p>
      </section>
    );
  }

  return (
    <section>
      <Link href="/" className="back-link">← Dashboard</Link>
      <h2 className="page-title">HeartBeat-konfiguration</h2>
      <p className="muted page-intro">
        Konfigurera hur collector-tjänsten kontaktar HeartBeat. Molntjänsten använder
        1Komma5 API (port 443). Lokal gateway kräver IP och port till enheten i ditt nätverk.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="card config-card">
          <h3 className="config-section-title">Anslutning</h3>
          <div className="form-grid">
            <label className="form-field">
              <span>Anslutningstyp</span>
              <select
                value={form.connection_type}
                onChange={(e) =>
                  handleConnectionTypeChange(e.target.value as "mock" | "cloud" | "local")
                }
              >
                <option value="mock">Mock (testdata)</option>
                <option value="cloud">1Komma5 molntjänst</option>
                <option value="local">Lokal gateway (IP/port)</option>
              </select>
            </label>

            <label className="form-field">
              <span>Poll-intervall (sekunder)</span>
              <input
                type="number"
                min={5}
                max={3600}
                value={form.poll_interval_seconds}
                onChange={(e) => updateField("poll_interval_seconds", Number(e.target.value))}
              />
            </label>
          </div>

          {form.connection_type !== "mock" && (
            <div className="form-grid">
              <label className="form-field">
                <span>{form.connection_type === "cloud" ? "API-värd" : "IP / värdnamn"}</span>
                <input
                  type="text"
                  value={form.host}
                  disabled={form.connection_type === "cloud"}
                  placeholder={form.connection_type === "local" ? "192.168.1.100" : ""}
                  onChange={(e) => updateField("host", e.target.value)}
                />
              </label>

              <label className="form-field">
                <span>Port</span>
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={form.port}
                  disabled={form.connection_type === "cloud"}
                  onChange={(e) => updateField("port", Number(e.target.value))}
                />
              </label>

              <label className="form-field form-field-checkbox">
                <input
                  type="checkbox"
                  checked={form.use_tls}
                  disabled={form.connection_type === "cloud"}
                  onChange={(e) => updateField("use_tls", e.target.checked)}
                />
                <span>Använd HTTPS</span>
              </label>

              <label className="form-field">
                <span>API-sökväg</span>
                <input
                  type="text"
                  value={form.api_path}
                  onChange={(e) => updateField("api_path", e.target.value)}
                />
              </label>
            </div>
          )}

          {config.api_url && (
            <p className="muted config-preview">
              Beräknad URL: <code>{config.api_url}</code>
            </p>
          )}
        </div>

        {form.connection_type === "cloud" && (
          <div className="card config-card">
            <h3 className="config-section-title">Autentisering (molntjänst)</h3>
            <p className="muted config-env-intro">
              1Komma5 HeartBeat API använder e-post/lösenord eller Bearer-token (JWT, ~24h).
            </p>
            <div className="form-grid">
              <label className="form-field">
                <span>E-post / användarnamn</span>
                <input
                  type="email"
                  value={form.username}
                  onChange={(e) => updateField("username", e.target.value)}
                />
              </label>
              <label className="form-field">
                <span>Lösenord</span>
                <input
                  type="password"
                  value={form.password}
                  placeholder={config.password_configured ? "•••••••• (oförändrat om tomt)" : ""}
                  onChange={(e) => updateField("password", e.target.value)}
                />
              </label>
              <label className="form-field form-field-wide">
                <span>Bearer-token (alternativ)</span>
                <input
                  type="password"
                  value={form.api_token}
                  placeholder={config.api_token_configured ? "•••••••• (oförändrat om tomt)" : ""}
                  onChange={(e) => updateField("api_token", e.target.value)}
                />
              </label>
            </div>
          </div>
        )}

        <div className="card config-card">
          <h3 className="config-section-title">Dashboard</h3>
          <p className="muted config-env-intro">
            Styr hur ofta dashboard och siddetaljer hämtar ny data från servern.
          </p>
          <div className="form-grid">
            <label className="form-field">
              <span>Uppdateringsintervall (sekunder)</span>
              <input
                type="number"
                min={1}
                max={30}
                value={form.dashboard_refresh_seconds}
                onChange={(e) => updateField("dashboard_refresh_seconds", Number(e.target.value))}
              />
            </label>
          </div>
        </div>

        {chargeAmps && (
          <div className="card config-card">
            <h3 className="config-section-title">Charge Amps (Halo-styrning)</h3>
            <dl className="config-list">
              <div className="config-row">
                <dt>Provider</dt>
                <dd>
                  {chargeAmps.effective_provider !== chargeAmps.provider
                    ? `${chargeAmps.effective_provider} (miljö: ${chargeAmps.provider})`
                    : chargeAmps.provider}
                </dd>
              </div>
              <div className="config-row">
                <dt>Mock-läge</dt>
                <dd>{chargeAmps.mock ? "Ja" : "Nej"}</dd>
              </div>
              <div className="config-row">
                <dt>API-nyckel</dt>
                <dd>
                  {chargeAmps.api_key_configured
                    ? chargeAmps.charger_api_keys_configured > 0 && !chargeAmps.env_api_key_configured
                      ? `Konfigurerad (${chargeAmps.charger_api_keys_configured} laddbox)`
                      : "Konfigurerad"
                    : "Saknas"}
                </dd>
              </div>
              <div className="config-row">
                <dt>Redo för produktion</dt>
                <dd>{chargeAmps.ready ? "Ja" : "Nej"}</dd>
              </div>
            </dl>
            {chargeAmps.notes.length > 0 && (
              <ul className="config-notes">
                {chargeAmps.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {readiness && (
          <div className="card config-card">
            <h3 className="config-section-title">Smart laddning – driftstatus</h3>
            <dl className="config-list">
              <div className="config-row">
                <dt>Aktiva bridge-laddboxar</dt>
                <dd>{readiness.active_bridge_chargers}</dd>
              </div>
              <div className="config-row">
                <dt>Drift redo</dt>
                <dd>{readiness.ready ? "Ja" : "Nej"}</dd>
              </div>
            </dl>
            {readiness.issues.length > 0 && (
              <ul className="config-notes">
                {readiness.issues.map((issue) => (
                  <li key={`${issue.site_slug}-${issue.charger_id}-${issue.code}`}>
                    {issue.site_slug}/{issue.charger_name}: {issue.message}
                  </li>
                ))}
              </ul>
            )}
            {readiness.notes.length > 0 && (
              <ul className="config-notes">
                {readiness.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {error && <p className="form-error">{error}</p>}
        {saveMessage && <p className="form-success">{saveMessage}</p>}

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Sparar…" : "Spara konfiguration"}
        </button>
      </form>

      <AppleDevicesAdminPanel />

      <div className="card config-card">
        <h3 className="config-section-title">Integrationer</h3>
        <ul className="config-notes">
          <li>
            <Link href="/admin/integrations/mercedes">Mercedes me — diagnostik och råattribut</Link>
          </li>
        </ul>
      </div>

      <SitesManager />

      <div className="card config-card">
        <h3 className="config-section-title">Status</h3>
        <dl className="config-list">
          <div className="config-row">
            <dt>Status</dt>
            <dd>{STATUS_LABELS[config.implementation_status] ?? config.implementation_status}</dd>
          </div>
          <div className="config-row">
            <dt>Kontaktande komponent</dt>
            <dd>{config.contacting_component}</dd>
          </div>
        </dl>
        {config.notes.length > 0 && (
          <ul className="config-notes">
            {config.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
