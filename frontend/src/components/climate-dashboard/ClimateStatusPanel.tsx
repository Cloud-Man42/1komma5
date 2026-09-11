"use client";

import { useEffect, useState } from "react";
import { getAdminToken } from "@/lib/adminAuth";

type ClimateDevice = {
  device_id: string;
  display_name?: string | null;
  temperature_c?: number | null;
  humidity_percent?: number | null;
  climate_mode?: string | null;
  target_temperature_c?: number | null;
  online?: boolean | null;
  source_quality?: string;
  observed_at?: string;
  vendor?: string | null;
};

export function ClimateStatusPanel({ siteSlug }: { siteSlug: string }) {
  const [devices, setDevices] = useState<ClimateDevice[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAdminToken();
    if (!token) {
      setError("Admin token required");
      return;
    }
    fetch(`/api/sites/${encodeURIComponent(siteSlug)}/climate/devices`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
      })
      .then((body) => setDevices(body.devices ?? []))
      .catch((err: Error) => setError(err.message));
  }, [siteSlug]);

  if (error) return <p role="alert">{error}</p>;
  if (devices.length === 0) {
    return <p data-testid="climate-empty">No climate devices configured.</p>;
  }

  return (
    <section data-testid="climate-status-panel">
      <h3>Climate (read-only)</h3>
      <div className="climate-grid">
        {devices.map((device) => (
          <article key={device.device_id} data-testid={`climate-device-${device.device_id}`}>
            <h4>{device.display_name || device.device_id}</h4>
            <p>Temp: {device.temperature_c ?? "—"} °C</p>
            <p>Humidity: {device.humidity_percent ?? "—"} %</p>
            <p>Mode: {device.climate_mode ?? "—"}</p>
            <p>Target: {device.target_temperature_c ?? "—"} °C</p>
            <p>Status: {device.online ? "Online" : "Offline"}</p>
            <p>Updated: {device.observed_at ?? "—"}</p>
            <p className="muted">Read-only integration — no control actions</p>
          </article>
        ))}
      </div>
    </section>
  );
}
