"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  VehicleIntegrationConfig,
  VehicleIntegrationLoginResult,
  fetchVehicleIntegrationConfig,
  loginVehicleIntegration,
  updateVehicleIntegrationConfig,
} from "@/lib/api";

export function MercedesAdminPanel({ siteSlug }: { siteSlug: string }) {
  const [config, setConfig] = useState<VehicleIntegrationConfig | null>(null);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loginResult, setLoginResult] = useState<VehicleIntegrationLoginResult | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchVehicleIntegrationConfig(siteSlug)
      .then(setConfig)
      .catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda Mercedes-config"));
  }, [siteSlug]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const updated = await updateVehicleIntegrationConfig(siteSlug, {
        enabled: form.get("enabled") === "true",
        region: String(form.get("region") || "Europe"),
        username: String(form.get("username") || ""),
        password: password || undefined,
        commands_enabled: form.get("commands_enabled") === "true",
      });
      setConfig(updated);
      setPassword("");
      setMessage("Mercedes me-inställningar sparade.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara");
    } finally {
      setSaving(false);
    }
  };

  const onLogin = async () => {
    setLoginResult(null);
    try {
      const result = await loginVehicleIntegration(siteSlug);
      setLoginResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inloggning misslyckades");
    }
  };

  if (!config) {
    return <p className="muted">Laddar Mercedes me-konfiguration…</p>;
  }

  return (
    <details className="card" open data-testid="mercedes-admin-panel">
      <summary>
        <strong>Mercedes me</strong>
      </summary>
      <form className="form-grid" onSubmit={onSubmit}>
        <label className="form-field">
          <span>Integration enabled</span>
          <select name="enabled" defaultValue={config.enabled ? "true" : "false"}>
            <option value="true">Ja</option>
            <option value="false">Nej</option>
          </select>
        </label>
        <label className="form-field">
          <span>Region</span>
          <select name="region" defaultValue={config.region}>
            <option value="Europe">Europe</option>
            <option value="North America">North America</option>
            <option value="Asia-Pacific">Asia-Pacific</option>
            <option value="China">China</option>
          </select>
        </label>
        <label className="form-field">
          <span>E-post</span>
          <input name="username" defaultValue={config.username} />
        </label>
        <label className="form-field">
          <span>Lösenord ({config.password_configured ? "konfigurerat" : "ej satt"})</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Lämna tom för oförändrat"
          />
        </label>
        <label className="form-field">
          <span>Kommandon (fas 8)</span>
          <select name="commands_enabled" defaultValue={config.commands_enabled ? "true" : "false"}>
            <option value="false">Avstängda</option>
            <option value="true">Aktiverade</option>
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving}>
            Spara Mercedes me
          </button>
          <button type="button" className="btn-secondary" onClick={onLogin}>
            Logga in
          </button>
        </div>
      </form>
      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
      {loginResult && <p className="form-success">{loginResult.message}</p>}
    </details>
  );
}
