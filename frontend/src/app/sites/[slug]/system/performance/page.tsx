"use client";

import { useEffect, useState } from "react";
import { fetchPerformanceMetrics, type PerformanceCenterMetrics } from "@/lib/api";

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
        Cache hit rate: {metrics.cache.hit_rate_pct}% ({metrics.cache.hits}/{metrics.cache.hits + metrics.cache.misses})
      </p>
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
