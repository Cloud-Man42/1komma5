"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  AppleDevice,
  AppleDeviceCreateResult,
  createAppleDevice,
  fetchAppleDevices,
  revokeAppleDevice,
} from "@/lib/api";

export function AppleDevicesAdminPanel() {
  const [devices, setDevices] = useState<AppleDevice[]>([]);
  const [ownerLabel, setOwnerLabel] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [deviceType, setDeviceType] = useState<"iphone" | "windows">("iphone");
  const [defaultSiteSlug, setDefaultSiteSlug] = useState("akarp");
  const [createdToken, setCreatedToken] = useState<AppleDeviceCreateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadDevices = async () => {
    setLoading(true);
    setError(null);
    try {
      setDevices(await fetchAppleDevices());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda widget-enheter");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDevices();
  }, []);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    setCreatedToken(null);
    try {
      const created = await createAppleDevice({
        owner_label: ownerLabel.trim(),
        device_name: deviceName.trim(),
        device_type: deviceType,
        default_site_slug: defaultSiteSlug || undefined,
      });
      setCreatedToken(created);
      setMessage("Enhet registrerad.");
      setOwnerLabel("");
      setDeviceName("");
      await loadDevices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte skapa enhet");
    } finally {
      setSaving(false);
    }
  };

  const onRevoke = async (deviceId: number) => {
    if (!window.confirm("Återkalla denna enhet? Widgeten slutar fungera.")) {
      return;
    }
    setError(null);
    try {
      await revokeAppleDevice(deviceId);
      setMessage("Enhet återkallad.");
      await loadDevices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte återkalla enhet");
    }
  };

  const copyToken = async () => {
    if (!createdToken?.token) return;
    await navigator.clipboard.writeText(createdToken.token);
    setMessage("Token kopierad.");
  };

  return (
    <div className="card config-card" data-testid="apple-devices-admin-panel">
      <h3 className="config-section-title">Widget-enheter</h3>
      <p className="muted config-env-intro">
        Registrera iPhone- och Windows-enheter för EMIC-widgeten. Token visas bara en gång vid skapande.
      </p>

      <form className="form-grid" onSubmit={onCreate}>
        <label className="form-field">
          <span>Ägare</span>
          <input value={ownerLabel} onChange={(e) => setOwnerLabel(e.target.value)} required />
        </label>
        <label className="form-field">
          <span>Enhetsnamn</span>
          <input value={deviceName} onChange={(e) => setDeviceName(e.target.value)} required />
        </label>
        <label className="form-field">
          <span>Plattform</span>
          <select value={deviceType} onChange={(e) => setDeviceType(e.target.value as "iphone" | "windows")}>
            <option value="iphone">iPhone (Apple Widget)</option>
            <option value="windows">Windows (taskbar)</option>
          </select>
        </label>
        <label className="form-field">
          <span>Standardplats</span>
          <select value={defaultSiteSlug} onChange={(e) => setDefaultSiteSlug(e.target.value)}>
            <option value="akarp">Demo Home</option>
            <option value="summer-house-denmark">Danmark</option>
            <option value="">Ingen</option>
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Skapar…" : "Skapa enhet"}
          </button>
        </div>
      </form>

      {createdToken && (
        <div className="card" data-testid="apple-device-token-once">
          <p className="form-success">
            Visas bara en gång — spara i Keychain (iPhone) eller EMIC Windows-inställningar.
          </p>
          <code>{createdToken.token}</code>
          <button type="button" className="btn-secondary" onClick={() => void copyToken()}>
            Kopiera token
          </button>
        </div>
      )}

      {loading ? (
        <p className="muted">Laddar enheter…</p>
      ) : (
        <table className="config-table">
          <thead>
            <tr>
              <th>Enhet</th>
              <th>Ägare</th>
              <th>Plattform</th>
              <th>Skapad</th>
              <th>Senast sedd</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.id}>
                <td>{device.device_name}</td>
                <td>{device.owner_label}</td>
                <td>{device.device_type === "windows" ? "Windows" : "iPhone"}</td>
                <td>{new Date(device.created_at).toLocaleString("sv-SE")}</td>
                <td>
                  {device.last_seen_at
                    ? new Date(device.last_seen_at).toLocaleString("sv-SE")
                    : "—"}
                </td>
                <td>{device.status === "active" ? "Aktiv" : "Återkallad"}</td>
                <td>
                  {device.status === "active" && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => void onRevoke(device.id)}
                    >
                      Återkalla
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
