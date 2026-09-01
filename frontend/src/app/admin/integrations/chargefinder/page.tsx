"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchChargeFinderDiagnostics,
  fetchChargeFinderRawLookup,
  fetchChargeFinderStatus,
  runChargeFinderTestLookup,
  type ChargeFinderDiagnosticsResponse,
  type ChargeFinderRawStation,
  type ChargeFinderStatusResponse,
} from "@/lib/api";

export default function ChargeFinderAdminPage() {
  const [status, setStatus] = useState<ChargeFinderStatusResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<ChargeFinderDiagnosticsResponse | null>(null);
  const [rawStations, setRawStations] = useState<ChargeFinderRawStation[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextStatus, nextDiagnostics] = await Promise.all([
        fetchChargeFinderStatus(),
        fetchChargeFinderDiagnostics(),
      ]);
      setStatus(nextStatus);
      setDiagnostics(nextDiagnostics);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function testMercedesLookup() {
    const result = await runChargeFinderTestLookup({ use_mercedes_position: true, site_slug: "akarp" });
    setMessage(`Hittade ${result.candidate_count} stationer nära Mercedes (${result.latitude.toFixed(5)}, ${result.longitude.toFixed(5)})`);
    setLat(String(result.latitude));
    setLon(String(result.longitude));
    await loadRaw(result.latitude, result.longitude);
  }

  async function testManualLookup() {
    const latitude = Number(lat);
    const longitude = Number(lon);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      setMessage("Ange giltig lat/lon");
      return;
    }
    const result = await runChargeFinderTestLookup({ latitude, longitude });
    setMessage(`Hittade ${result.candidate_count} stationer`);
    await loadRaw(latitude, longitude);
  }

  async function loadRaw(latitude: number, longitude: number) {
    const raw = await fetchChargeFinderRawLookup(latitude, longitude);
    setRawStations(raw.stations);
  }

  return (
    <main className="page-shell">
      <div className="page-header">
        <div>
          <p className="page-kicker">Admin</p>
          <h1>ChargeFinder Integration</h1>
          <p className="page-subtitle">Diagnostik, test lookup och maskerad rådata för laddstationsidentifiering.</p>
        </div>
        <Link href="/config" className="btn btn-secondary">Tillbaka till config</Link>
      </div>

      {message ? <p className="notice notice-info">{message}</p> : null}
      {loading ? <p>Laddar…</p> : null}

      {status ? (
        <section className="card">
          <h2>Status</h2>
          <dl className="kv-grid">
            <dt>Health</dt><dd>{diagnostics?.health_status ?? status.health_status}</dd>
            <dt>Enabled</dt><dd>{status.enabled ? "Ja" : "Nej"}</dd>
            <dt>Mode</dt><dd>{status.mode}</dd>
            <dt>Sökradie</dt><dd>{status.search_radius_m} m</dd>
            <dt>Cache TTL</dt><dd>{status.cache_ttl_seconds}s</dd>
            <dt>Cache hits</dt><dd>{status.cache_hits}</dd>
            <dt>Cache misses</dt><dd>{status.cache_misses}</dd>
            <dt>Parser failures</dt><dd>{status.parser_failures}</dd>
            <dt>Blocked until</dt><dd>{status.blocked_until ?? "—"}</dd>
            <dt>Last error</dt><dd>{status.last_error ?? "—"}</dd>
            <dt>Latency</dt><dd>{status.last_latency_ms != null ? `${status.last_latency_ms} ms` : "—"}</dd>
            <dt>Browser</dt><dd>{status.browser_status ?? "—"}</dd>
            <dt>Parser version</dt><dd>{status.parsing_version}</dd>
          </dl>
        </section>
      ) : null}

      <section className="card">
        <h2>Test ChargeFinder lookup</h2>
        <div className="button-row">
          <button type="button" className="btn btn-secondary" onClick={() => void testMercedesLookup()}>
            Använd Mercedes-position
          </button>
        </div>
        <div className="form-row">
          <label>
            Lat
            <input value={lat} onChange={(e) => setLat(e.target.value)} />
          </label>
          <label>
            Lon
            <input value={lon} onChange={(e) => setLon(e.target.value)} />
          </label>
          <button type="button" className="btn btn-secondary" onClick={() => void testManualLookup()}>
            Test lookup
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Raw Data Inspector</h2>
        <p>Maskerade ChargeFinder-fält.</p>
        {rawStations.length === 0 ? (
          <p>Kör test lookup för att se rådata.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Operatör</th>
                <th>Station</th>
                <th>Avstånd</th>
                <th>Typ</th>
                <th>kW</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {rawStations.map((row) => (
                <tr key={row.provider_station_id}>
                  <td>{row.provider_station_id}</td>
                  <td>{row.operator ?? "—"}</td>
                  <td>{row.station_name ?? "—"}</td>
                  <td>{row.distance_m != null ? `${Math.round(row.distance_m)} m` : "—"}</td>
                  <td>{row.charging_type ?? "—"}</td>
                  <td>{row.max_power_kw ?? "—"}</td>
                  <td>{row.external_url ? <a href={row.external_url} target="_blank" rel="noreferrer">Öppna</a> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
