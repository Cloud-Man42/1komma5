"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchMarketplaceArtifactSecurity,
  fetchMarketplaceCatalog,
  fetchMarketplaceRelease,
  type MarketplaceArtifactSecurity,
  type MarketplaceCatalogRelease,
  type MarketplaceFetchResult,
} from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";

export function MarketplaceSecurityPanel() {
  const [releases, setReleases] = useState<MarketplaceCatalogRelease[]>([]);
  const [selected, setSelected] = useState<MarketplaceFetchResult | null>(null);
  const [security, setSecurity] = useState<MarketplaceArtifactSecurity | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin-token krävs.");
      return;
    }
    setError(null);
    try {
      const catalog = await fetchMarketplaceCatalog();
      setReleases(catalog.releases);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda katalog");
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  async function fetchRelease(release: MarketplaceCatalogRelease) {
    const key = `${release.module_id}@${release.version}`;
    setBusyKey(key);
    setError(null);
    setSelected(null);
    setSecurity(null);
    try {
      const result = await fetchMarketplaceRelease(release.module_id, release.version);
      setSelected(result);
      setSecurity(await fetchMarketplaceArtifactSecurity(result.artifact_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fetch misslyckades");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="config-page" data-testid="marketplace-security-panel">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <h1 className="config-page-title">Marketplace release security</h1>
        <p className="config-page-lead">Trusted catalog releases — staging only. Runtime remains blocked until Step 5C.5.</p>
      </header>
      {error ? <p className="config-error">{error}</p> : null}
      <section className="config-panel">
        <h2 className="config-panel-title">Catalog releases</h2>
        {releases.length === 0 ? <p className="muted">Inga releases i trusted catalog.</p> : null}
        <ul className="config-list">
          {releases.map((release) => {
            const key = `${release.module_id}@${release.version}`;
            return (
              <li key={key} data-testid={`release-${release.module_id}-${release.version}`}>
                <strong>{release.module_id}</strong> v{release.version} · {release.publisher_id}
                <button
                  type="button"
                  className="config-button"
                  disabled={busyKey === key}
                  onClick={() => void fetchRelease(release)}
                >
                  {busyKey === key ? "Hämtar…" : "Fetch & stage"}
                </button>
              </li>
            );
          })}
        </ul>
      </section>
      {selected ? (
        <section className="config-panel" data-testid="release-security-detail">
          <h2 className="config-panel-title">Release security detail</h2>
          <p>State: {selected.state}</p>
          <p>Policy: {selected.policy_decision ?? "—"}</p>
          <p>Reason codes: {selected.reason_codes.join(", ") || "—"}</p>
          {security ? (
            <>
              <p data-testid="runtime-blocked">{security.runtime_message}</p>
              <p>Integrity: {security.integrity_verified ? "verified" : "failed"}</p>
              <p>SBOM: {security.sbom_status}</p>
              <p>Advisories: {security.advisory_status}</p>
              <p>Severity: {security.highest_severity}</p>
              <p>Vulnerabilities: {security.vulnerability_count}</p>
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
