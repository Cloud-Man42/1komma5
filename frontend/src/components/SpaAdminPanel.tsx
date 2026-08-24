"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  SpaConfig,
  SpaConnectionTest,
  fetchSpaConfig,
  testSpaConnection,
  updateSpaConfig,
} from "@/lib/api";

export function SpaAdminPanel({ siteSlug }: { siteSlug: string }) {
  const [config, setConfig] = useState<SpaConfig | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<SpaConnectionTest | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSpaConfig(siteSlug)
      .then(setConfig)
      .catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda spa-config"));
  }, [siteSlug]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const updated = await updateSpaConfig(siteSlug, {
        integration_enabled: form.get("integration_enabled") === "true",
        api_base_url: String(form.get("api_base_url") || ""),
        api_key: apiKey || undefined,
        external_spa_id: String(form.get("external_spa_id") || ""),
        poll_interval_seconds: Number(form.get("poll_interval_seconds") || 60),
        energy_collection_enabled: form.get("energy_collection_enabled") === "true",
        cost_calculation_enabled: form.get("cost_calculation_enabled") === "true",
      });
      setConfig(updated);
      setApiKey("");
      setMessage("Arctic Spa-inställningar sparade.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara");
    } finally {
      setSaving(false);
    }
  };

  const onTest = async () => {
    setTestResult(null);
    try {
      const result = await testSpaConnection(siteSlug);
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test misslyckades");
    }
  };

  if (!config) {
    return <p className="muted">Laddar Arctic Spa-konfiguration…</p>;
  }

  return (
    <details className="card" open data-testid="spa-admin-panel">
      <summary>
        <strong>Arctic Spa</strong>
      </summary>
      <form className="form-grid" onSubmit={onSubmit}>
        <label className="form-field">
          <span>Integration enabled</span>
          <select name="integration_enabled" defaultValue={config.integration_enabled ? "true" : "false"}>
            <option value="true">Ja</option>
            <option value="false">Nej</option>
          </select>
        </label>
        <label className="form-field">
          <span>API base URL</span>
          <input name="api_base_url" defaultValue={config.api_base_url} />
        </label>
        <label className="form-field">
          <span>API key ({config.masked_api_key || "ej satt"})</span>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Lämna tom för oförändrat" />
        </label>
        <label className="form-field">
          <span>Spa ID</span>
          <input name="external_spa_id" defaultValue={config.external_spa_id} />
        </label>
        <label className="form-field">
          <span>Poll-intervall (s)</span>
          <input name="poll_interval_seconds" type="number" min={15} max={600} defaultValue={config.poll_interval_seconds} />
        </label>
        <label className="form-field">
          <span>Energy collection</span>
          <select name="energy_collection_enabled" defaultValue={config.energy_collection_enabled ? "true" : "false"}>
            <option value="true">Ja</option>
            <option value="false">Nej</option>
          </select>
        </label>
        <label className="form-field">
          <span>Cost calculation</span>
          <select name="cost_calculation_enabled" defaultValue={config.cost_calculation_enabled ? "true" : "false"}>
            <option value="true">Ja</option>
            <option value="false">Nej</option>
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving}>
            Spara Arctic Spa
          </button>
          <button type="button" className="btn-secondary" onClick={onTest}>
            Testa anslutning
          </button>
        </div>
      </form>
      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
      {testResult && (
        <p className={testResult.success ? "form-success" : "form-error"}>
          {testResult.message}
          {testResult.last_update ? ` · ${new Date(testResult.last_update).toLocaleString("sv-SE")}` : ""}
        </p>
      )}
    </details>
  );
}
