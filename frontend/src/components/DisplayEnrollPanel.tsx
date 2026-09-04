"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";

import {
  AppleDevice,
  AppleDeviceCreateResult,
  createAppleDevice,
  fetchAppleDevices,
  fetchSites,
  revokeAppleDevice,
  type Site,
} from "@/lib/api";
import {
  buildDisplayEnrollUrl,
  displayDeviceTypeLabel,
  displayHomePath,
  isDisplayDevice,
  type DisplayDeviceType,
} from "@/lib/displayEnroll";

function DisplayEnrollQr({ url }: { url: string }) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    void QRCode.toDataURL(url, {
      margin: 1,
      width: 220,
      color: { dark: "#0f172a", light: "#ffffff" },
    })
      .then((value) => {
        if (!cancelled) setDataUrl(value);
      })
      .catch(() => {
        if (!cancelled) setError("Kunde inte skapa QR-kod.");
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (error) return <p className="form-error">{error}</p>;
  if (!dataUrl) return <p className="muted">Skapar QR-kod…</p>;
  return (
    <img
      src={dataUrl}
      alt="QR-kod för väggdisplay"
      className="display-enroll-qr"
      width={220}
      height={220}
    />
  );
}

export function DisplayEnrollPanel() {
  const [sites, setSites] = useState<Site[]>([]);
  const [devices, setDevices] = useState<AppleDevice[]>([]);
  const [ownerLabel, setOwnerLabel] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [deviceType, setDeviceType] = useState<DisplayDeviceType>("phone");
  const [siteSlug, setSiteSlug] = useState("akarp");
  const [created, setCreated] = useState<AppleDeviceCreateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const enrollUrl = useMemo(() => {
    if (!created?.token) return null;
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return buildDisplayEnrollUrl(origin, created.token, siteSlug);
  }, [created?.token, siteSlug]);

  const displayDevices = useMemo(() => devices.filter(isDisplayDevice), [devices]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [siteList, deviceList] = await Promise.all([fetchSites(), fetchAppleDevices()]);
      setSites(siteList);
      setDevices(deviceList);
      if (siteList.length > 0 && !siteList.some((site) => site.slug === siteSlug)) {
        setSiteSlug(siteList[0].slug);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda väggdisplay-inställningar");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    setCreated(null);
    try {
      const result = await createAppleDevice({
        owner_label: ownerLabel.trim(),
        device_name: deviceName.trim(),
        device_type: deviceType,
        default_site_slug: siteSlug,
      });
      setCreated(result);
      setMessage("Enhet skapad. Skanna QR-koden eller öppna länken på mobilen/surfplattan.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte skapa enhet");
    } finally {
      setSaving(false);
    }
  };

  const copyEnrollLink = async () => {
    if (!enrollUrl) return;
    await navigator.clipboard.writeText(enrollUrl);
    setMessage("Aktiveringslänk kopierad.");
  };

  const onRevoke = async (deviceId: number) => {
    if (!window.confirm("Återkalla denna enhet? Väggdisplayen slutar fungera tills du aktiverar igen.")) {
      return;
    }
    setError(null);
    try {
      await revokeAppleDevice(deviceId);
      setMessage("Enhet återkallad.");
      if (created?.id === deviceId) setCreated(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte återkalla enhet");
    }
  };

  return (
    <div className="card config-card" data-testid="display-enroll-panel">
      <h3 className="config-section-title">Väggdisplay — mobil &amp; surfplatta</h3>
      <p className="muted config-env-intro">
        Skapa en aktiveringslänk till samma vy som Pi-skärmen (<code>/display/…</code>).
        Skanna QR-koden på telefonen eller surfplattan — du behöver bara göra det en gång per enhet.
      </p>

      <form className="form-grid" onSubmit={(event) => void onCreate(event)}>
        <label className="form-field">
          <span>Ägare</span>
          <input
            value={ownerLabel}
            onChange={(event) => setOwnerLabel(event.target.value)}
            aria-label="Ägare"
            required
          />
        </label>
        <label className="form-field">
          <span>Enhetsnamn</span>
          <input
            value={deviceName}
            onChange={(event) => setDeviceName(event.target.value)}
            aria-label="Enhetsnamn"
            placeholder="Henriks iPhone"
            required
          />
        </label>
        <label className="form-field">
          <span>Enhetstyp</span>
          <select
            value={deviceType}
            aria-label="Enhetstyp"
            onChange={(event) => setDeviceType(event.target.value as DisplayDeviceType)}
          >
            <option value="phone">Mobiltelefon</option>
            <option value="tablet">Surfplatta</option>
          </select>
        </label>
        <label className="form-field">
          <span>Plats</span>
          <select value={siteSlug} aria-label="Plats" onChange={(event) => setSiteSlug(event.target.value)}>
            {(sites.length > 0 ? sites : [{ slug: "akarp", name: "Åkarp" } as Site]).map((site) => (
              <option key={site.slug} value={site.slug}>
                {site.name}
              </option>
            ))}
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Skapar…" : "Skapa aktiveringslänk"}
          </button>
        </div>
      </form>

      {created && enrollUrl ? (
        <div className="display-enroll-result" data-testid="display-enroll-result">
          <p className="form-success">
            Öppna länken på samma enhet, eller skanna QR-koden med kameran. Du hamnar på{" "}
            <code>{displayHomePath(siteSlug)}</code> och behöver inte logga in igen på ett år.
          </p>
          <div className="display-enroll-result-body">
            <DisplayEnrollQr url={enrollUrl} />
            <div className="display-enroll-actions">
              <a href={enrollUrl} className="btn-primary display-enroll-open-link">
                Öppna väggdisplay
              </a>
              <button type="button" className="btn-secondary" onClick={() => void copyEnrollLink()}>
                Kopiera aktiveringslänk
              </button>
              <p className="muted display-enroll-url">
                <code>{enrollUrl}</code>
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {loading ? (
        <p className="muted">Laddar registrerade enheter…</p>
      ) : displayDevices.length > 0 ? (
        <table className="config-table">
          <thead>
            <tr>
              <th>Enhet</th>
              <th>Ägare</th>
              <th>Typ</th>
              <th>Plats</th>
              <th>Senast sedd</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {displayDevices.map((device) => (
              <tr key={device.id}>
                <td>{device.device_name}</td>
                <td>{device.owner_label}</td>
                <td>{displayDeviceTypeLabel(device.device_type)}</td>
                <td>{device.default_site_slug ?? "—"}</td>
                <td>
                  {device.last_seen_at
                    ? new Date(device.last_seen_at).toLocaleString("sv-SE")
                    : "—"}
                </td>
                <td>{device.status === "active" ? "Aktiv" : "Återkallad"}</td>
                <td>
                  {device.status === "active" ? (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => void onRevoke(device.id)}
                    >
                      Återkalla
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">Inga väggdisplay-enheter registrerade ännu.</p>
      )}

      {message ? <p className="form-success">{message}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </div>
  );
}
