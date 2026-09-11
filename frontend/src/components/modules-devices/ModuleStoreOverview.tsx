"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  analyzeCatalogImpact,
  fetchMarketplaceMetadataStatus,
  fetchStoreOverview,
  installCatalogEntry,
  validateCatalogEntry,
  type CatalogEntry,
  type MarketplaceMetadataStatus,
  type PackageImpactResult,
  type PackageStoreCard,
  type PackageValidationResult,
  type StoreOverviewResponse,
} from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { PackageReviewPanel } from "@/components/modules-devices/PackageReviewPanel";
import { packageStateLabel, trustBadgeLabel } from "@/components/modules-devices/packageErrorLabels";

function PackageCard({ pkg }: { pkg: PackageStoreCard }) {
  return (
    <article className="config-panel" data-testid={`store-package-${pkg.module_id}`}>
      <div className="config-panel-header">
        <div>
          <h3 className="config-panel-title">{pkg.name}</h3>
          <p className="muted">{pkg.module_id} · v{pkg.installed_version}</p>
        </div>
        <span className={pkg.package_state === "quarantined" ? "config-badge danger" : "config-badge"}>
          {packageStateLabel(pkg.package_state)}
        </span>
      </div>
      <div className="config-stat-grid">
        <div><span className="config-stat-label">Publisher</span><strong>{pkg.publisher}</strong></div>
        <div><span className="config-stat-label">Trust</span><strong>{trustBadgeLabel("publisher_trusted", pkg.publisher_trusted)}</strong></div>
        <div><span className="config-stat-label">Sites enabled</span><strong>{pkg.enabled_sites.length}</strong></div>
        <div><span className="config-stat-label">Runtime</span><strong>{pkg.runtime_status ?? "—"}</strong></div>
      </div>
      {pkg.version_match === false ? (
        <p className="config-error">Installed: {pkg.installed_version} · Runtime: {pkg.runtime_version ?? "—"}</p>
      ) : null}
      {pkg.checksum_match === false ? <p className="config-error">Runtime package differs from installed package.</p> : null}
      {pkg.restart_required ? <p className="config-banner">Omstart krävs innan modulen blir tillgänglig.</p> : null}
      {pkg.attention_reasons.length ? (
        <p className="config-error">Behöver uppmärksamhet: {pkg.attention_reasons.join(", ")}</p>
      ) : null}
      <Link href={`/config/modules-devices/store/${encodeURIComponent(pkg.module_id)}`} className="config-button">
        Visa paketdetaljer
      </Link>
    </article>
  );
}

function CatalogCard({ entry, onInstalled }: { entry: CatalogEntry; onInstalled: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<PackageValidationResult | null>(null);
  const [impact, setImpact] = useState<PackageImpactResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  async function reviewCatalogEntry() {
    setBusy(true);
    setError(null);
    setConfirmed(false);
    try {
      const result = await validateCatalogEntry(entry.entry_id);
      setValidation(result);
      setImpact(await analyzeCatalogImpact(entry.entry_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validering misslyckades");
      setValidation(null);
      setImpact(null);
    } finally {
      setBusy(false);
    }
  }

  async function installFromCatalog() {
    if (!validation?.install_allowed) return;
    setBusy(true);
    setError(null);
    try {
      await installCatalogEntry(entry.entry_id);
      setValidation(null);
      setImpact(null);
      setConfirmed(false);
      onInstalled();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Installation misslyckades");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="config-panel" data-testid={`catalog-entry-${entry.entry_id}`}>
      <h3 className="config-panel-title">{entry.name}</h3>
      <p className="muted">{entry.module_id} · v{entry.version}</p>
      <p>{entry.description}</p>
      <p className="muted">Publisher: {entry.publisher}</p>
      {error ? <p className="config-error">{error}</p> : null}
      {!validation ? (
        <button type="button" className="config-button" disabled={busy} onClick={() => void reviewCatalogEntry()}>
          {busy ? "Validerar…" : "Granska katalogpaket"}
        </button>
      ) : (
        <>
          <PackageReviewPanel validation={validation} impact={impact} />
          <button type="button" className="config-button" disabled={!validation.install_allowed || busy} onClick={() => setConfirmed(true)}>
            Bekräfta installation
          </button>
          {confirmed ? (
            <button type="button" className="config-button" disabled={busy} onClick={() => void installFromCatalog()}>
              {busy ? "Installerar…" : "Installera från intern katalog"}
            </button>
          ) : null}
        </>
      )}
    </article>
  );
}

function marketplaceHealthLabel(status: MarketplaceMetadataStatus | null): string {
  if (!status?.enabled) return "Inaktiverad";
  switch (status.metadata_health) {
    case "healthy":
      return "Healthy";
    case "stale":
      return "Stale";
    case "expired":
      return "Expired";
    case "offline":
      return "Offline";
    case "invalid":
      return "Invalid";
    case "unavailable":
      return "Unavailable";
    default:
      return "Uninitialized";
  }
}

function revocationLabel(status: MarketplaceMetadataStatus | null): string {
  if (!status?.enabled) return "—";
  switch (status.revocation_freshness) {
    case "fresh":
      return "Fresh";
    case "stale":
      return "Stale";
    case "expired":
      return "Expired";
    default:
      return "Unavailable";
  }
}

export function ModuleStoreOverview() {
  const [overview, setOverview] = useState<StoreOverviewResponse | null>(null);
  const [marketplaceStatus, setMarketplaceStatus] = useState<MarketplaceMetadataStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const hasToken = typeof window !== "undefined" && Boolean(getAdminToken());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [storeOverview, metadataStatus] = await Promise.all([
        fetchStoreOverview(),
        fetchMarketplaceMetadataStatus().catch(() => null),
      ]);
      setOverview(storeOverview);
      setMarketplaceStatus(metadataStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda Module Store");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasToken) void load();
    else {
      setLoading(false);
      setError("Admin-token krävs. Lägg till token under Admin & säkerhet.");
    }
  }, [hasToken, load]);

  return (
    <div className="config-page" data-testid="module-store-overview">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <div>
          <h1 className="config-page-title">Module Store</h1>
          <p className="config-page-lead">Intern betrodd modulbutik — endast signerade packages från trusted publishers.</p>
        </div>
        <Link href="/config/modules-devices/store/upload" className="config-button">
          Ladda upp paket
        </Link>
      </header>

      {overview?.allow_unsigned_modules ? (
        <p className="config-banner">Dev-läge: osignerade paket kan tillåtas av backend-policy.</p>
      ) : (
        <p className="config-banner">Prod-policy: osignerade paket blockeras. Trust avgörs av backend.</p>
      )}

      {marketplaceStatus ? (
        <section className="config-panel" data-testid="marketplace-metadata-status">
          <h2 className="config-panel-title">Marketplace metadata</h2>
          <div className="config-stat-grid">
            <div><span className="config-stat-label">Catalog</span><strong>{marketplaceHealthLabel(marketplaceStatus)}</strong></div>
            <div><span className="config-stat-label">Revocation data</span><strong>{revocationLabel(marketplaceStatus)}</strong></div>
            <div><span className="config-stat-label">Last sync</span><strong>{marketplaceStatus.last_sync ?? "—"}</strong></div>
            <div><span className="config-stat-label">Root version</span><strong>{marketplaceStatus.root_version ?? "—"}</strong></div>
          </div>
          {marketplaceStatus.last_error ? <p className="config-error">{marketplaceStatus.last_error}</p> : null}
        </section>
      ) : null}

      {error ? <p className="config-error">{error}</p> : null}
      {loading ? <p className="muted">Laddar…</p> : null}

      {overview ? (
        <>
          <section className="config-panel">
            <h2 className="config-panel-title">Behöver uppmärksamhet</h2>
            {overview.needs_attention.length ? (
              <div className="config-stack">{overview.needs_attention.map((pkg) => <PackageCard key={pkg.module_id} pkg={pkg} />)}</div>
            ) : (
              <p className="muted">Inga paket behöver uppmärksamhet.</p>
            )}
          </section>

          <section className="config-panel">
            <h2 className="config-panel-title">Installerade</h2>
            {overview.installed.length ? (
              <div className="config-stack">{overview.installed.map((pkg) => <PackageCard key={pkg.module_id} pkg={pkg} />)}</div>
            ) : (
              <p className="muted">Inga installerade paket.</p>
            )}
          </section>

          <section className="config-panel">
            <h2 className="config-panel-title">Tillgängliga betrodda paket</h2>
            {overview.catalog.length ? (
              <div className="config-stack">
                {overview.catalog.map((entry) => (
                  <CatalogCard key={entry.entry_id} entry={entry} onInstalled={load} />
                ))}
              </div>
            ) : (
              <p className="muted">Ingen intern katalog konfigurerad.</p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
