"use client";

import { useEffect, useState } from "react";
import { fetchPerformanceMetrics, type PerformanceCenterMetrics } from "@/lib/api";

function formatAge(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.round(seconds / 60)} min`;
}

export default function PerformanceCenterPage() {
  const [metrics, setMetrics] = useState<PerformanceCenterMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await fetchPerformanceMetrics();
        if (active) setMetrics(data);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Kunde inte ladda prestandadata");
      }
    };
    load();
    const interval = setInterval(load, 10_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (error) return <p className="text-danger">{error}</p>;
  if (!metrics) return <p>Laddar prestandadata…</p>;

  return (
    <section className="panel">
      <h1>Performance Center</h1>
      <p>API-anrop: {metrics.request_count}</p>
      <p>
        Cache hit rate: {metrics.cache.hit_rate_pct}% ({metrics.cache.hits}/
        {metrics.cache.hits + metrics.cache.misses})
        {metrics.cache.backend ? ` · ${metrics.cache.backend}` : null}
        {metrics.cache.redis_configured && !metrics.cache.redis_available ? " · Redis otillgänglig" : null}
      </p>

      <h2>Snapshot per site</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Site</th>
            <th>Ålder</th>
            <th>Freshness</th>
          </tr>
        </thead>
        <tbody>
          {metrics.site_snapshots.map((row) => (
            <tr key={row.site_slug}>
              <td>{row.site_name}</td>
              <td>{formatAge(row.age_seconds)}</td>
              <td>{row.freshness}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Collector lanes</h2>
      {metrics.tasks && metrics.tasks.sample_size > 0 ? (
        <>
          <p>
            Samples: {metrics.tasks.sample_size}, failures: {metrics.tasks.failures}
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Lane</th>
                <th>Runs</th>
                <th>p50</th>
                <th>p95</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.tasks.lanes).map(([lane, stats]) => (
                <tr key={lane}>
                  <td>{lane}</td>
                  <td>{stats.count}</td>
                  <td>{stats.p50_ms} ms</td>
                  <td>{stats.p95_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p>Ingen collector-taskdata ännu.</p>
      )}

      <h2>Långsammaste routes</h2>
      <ul>
        {metrics.slowest_routes.map((row) => (
          <li key={row.route}>
            {row.route} — p50 {row.p50_ms} ms, p95 {row.p95_ms} ms ({row.count} anrop)
          </li>
        ))}
      </ul>
      <h2>Providers</h2>
      <ul>
        {metrics.providers.map((row) => (
          <li key={row.provider}>
            {row.provider} — snitt {row.avg_ms} ms, {row.errors} fel
          </li>
        ))}
      </ul>
    </section>
  );
}
