"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SolarAccuracyView } from "@/components/SolarAccuracyView";
import { SolarDiagnosticsPanel } from "@/components/SolarDiagnosticsPanel";
import { fetchSolarConfig, fetchSolarModelMetrics, fetchSolarProviderStatus } from "@/lib/api";
import { SMHI_ATTRIBUTION, smhiAttributionLine } from "@/lib/solarAttribution";

interface SolarIntelligencePageClientProps {
  siteSlug: string;
}

export function SolarIntelligencePageClient({ siteSlug }: SolarIntelligencePageClientProps) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [providers, setProviders] = useState<Array<{ provider: string; status: string }>>([]);
  const [metrics, setMetrics] = useState<{ model_version: string | null; wape: number | null } | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const config = await fetchSolarConfig(siteSlug);
        if (!active) return;
        setEnabled(config.solar_intelligence_enabled ?? false);
        if (config.solar_intelligence_enabled) {
          const [status, modelMetrics] = await Promise.all([
            fetchSolarProviderStatus(siteSlug).catch(() => ({ providers: [] })),
            fetchSolarModelMetrics(siteSlug).catch(() => null),
          ]);
          if (active) {
            setProviders(status.providers ?? []);
            setMetrics(modelMetrics);
          }
        }
      } catch {
        if (active) setEnabled(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [siteSlug]);

  if (enabled === null) return <p className="muted">Laddar Solar Intelligence…</p>;

  if (!enabled) {
    return (
      <section>
        <h2>Solar Intelligence</h2>
        <p className="muted">
          Solar Intelligence är inte aktiverad för denna anläggning. Aktivera under Inställningar när SMHI-data
          och backfill är klara.
        </p>
        <Link href="/config" className="back-link">
          Gå till inställningar →
        </Link>
      </section>
    );
  }

  return (
    <div className="solar-intelligence-page">
      <h2>Solar Intelligence</h2>
      <p className="muted">{smhiAttributionLine()}</p>

      <section className="peaks-section">
        <h3 className="section-title">Provider-status</h3>
        {providers.length === 0 ? (
          <p className="muted">Ingen provider-status ännu — kör en prognosuppdatering.</p>
        ) : (
          <ul>
            {providers.map((p) => (
              <li key={p.provider}>
                {p.provider}: {p.status}
              </li>
            ))}
          </ul>
        )}
      </section>

      {metrics ? (
        <section className="peaks-section">
          <h3 className="section-title">Champion-modell</h3>
          <p>
            {metrics.model_version ?? "—"} · WAPE {metrics.wape != null ? `${metrics.wape.toFixed(1)} %` : "—"}
          </p>
        </section>
      ) : null}

      <SolarAccuracyView siteSlug={siteSlug} />
      <SolarDiagnosticsPanel siteSlug={siteSlug} />

      <footer className="solar-attribution">
        <p>
          <strong>{SMHI_ATTRIBUTION.title}</strong>
        </p>
        <p className="muted">{SMHI_ATTRIBUTION.body}</p>
        <a href={SMHI_ATTRIBUTION.linkUrl} target="_blank" rel="noopener noreferrer">
          {SMHI_ATTRIBUTION.linkLabel}
        </a>
      </footer>
    </div>
  );
}
