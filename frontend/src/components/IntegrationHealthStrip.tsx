"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchIntegrationHealth, type IntegrationHealthResponse } from "@/lib/api";
import { integrationProviderLabelSv } from "@/lib/integrationHealthLabels";

function alertProviders(data: IntegrationHealthResponse): number {
  return data.providers.filter(
    (row) => row.status !== "ok" || row.consecutive_failures >= 3,
  ).length;
}

export function IntegrationHealthStrip({ siteSlug }: { siteSlug: string }) {
  const [data, setData] = useState<IntegrationHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchIntegrationHealth(siteSlug)
      .then((payload) => {
        if (!active) return;
        setData(payload);
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setData(null);
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  const alerts = data ? alertProviders(data) : 0;
  const worst = data?.providers.find((row) => row.status !== "ok" || row.consecutive_failures >= 3);

  return (
    <div className="idash-health-strip" data-testid="integration-health-strip">
      {error && !data ? <span>Integrationshälsa otillgänglig</span> : null}
      {!data && !error ? <span>Hämtar integrationshälsa…</span> : null}
      {data ? (
        <>
          {alerts === 0 ? (
            <span className="idash-health-strip-ok">
              {data.providers.length} integrationer OK
            </span>
          ) : (
            <span className="idash-health-strip-warn" data-testid="integration-health-strip-alert">
              {alerts} integration(er) behöver uppmärksamhet
              {worst ? ` — ${integrationProviderLabelSv(worst.provider)}: ${worst.status}` : ""}
            </span>
          )}
          <Link href={`/sites/${siteSlug}/diagnostics`} className="idash-health-strip-link">
            Diagnostik
          </Link>
        </>
      ) : null}
    </div>
  );
}
