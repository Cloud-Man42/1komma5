"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  analyzePackageImpact,
  fetchPackageSiteActivations,
  fetchPackageStoreDetail,
  removeModulePackage,
  rollbackModulePackage,
  type PackageImpactResult,
  type PackageSiteActivation,
  type PackageStoreCard,
} from "@/lib/api";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { packageErrorLabel, packageStateLabel, trustBadgeLabel } from "@/components/modules-devices/packageErrorLabels";

type Props = {
  moduleId: string;
};

export function PackageStoreDetailPanel({ moduleId }: Props) {
  const [pkg, setPkg] = useState<PackageStoreCard | null>(null);
  const [sites, setSites] = useState<PackageSiteActivation[]>([]);
  const [rollbackImpact, setRollbackImpact] = useState<PackageImpactResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    setPkg(await fetchPackageStoreDetail(moduleId));
    setSites(await fetchPackageSiteActivations(moduleId));
  }, [moduleId]);

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda paket"));
  }, [load]);

  async function prepareRollback() {
    setShowRollbackConfirm(true);
    setRollbackImpact(await analyzePackageImpact(moduleId));
  }

  async function runRollback() {
    setBusy(true);
    setActionMessage(null);
    try {
      const result = await rollbackModulePackage(moduleId);
      setActionMessage(result.message);
      setShowRollbackConfirm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback misslyckades");
    } finally {
      setBusy(false);
    }
  }

  async function runRemove() {
    setBusy(true);
    setActionMessage(null);
    try {
      const impact = await analyzePackageImpact(moduleId);
      if (impact.affected_sites.length || impact.affected_devices.length || impact.affected_modules.length) {
        setError(
          `Remove blocked: sites=${impact.affected_sites.join(", ") || "—"} devices=${impact.affected_devices.join(", ") || "—"} modules=${impact.affected_modules.join(", ") || "—"}`,
        );
        return;
      }
      const result = await removeModulePackage(moduleId);
      setActionMessage(result.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Remove misslyckades");
    } finally {
      setBusy(false);
    }
  }

  if (!pkg) {
    return error ? <p className="config-error">{error}</p> : <p className="muted">Laddar paket…</p>;
  }

  const quarantined = pkg.package_state === "quarantined";
  const meta = pkg.metadata;

  return (
    <div className="config-page" data-testid="package-store-detail">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <div>
          <Link href="/config/modules-devices/store">← Module Store</Link>
          <h1 className="config-page-title">{pkg.name}</h1>
          <p className="config-page-lead">{pkg.module_id} · v{pkg.installed_version}</p>
        </div>
      </header>

      {error ? <p className="config-error">{error}</p> : null}
      {actionMessage ? <p className="config-banner">{actionMessage}</p> : null}
      {pkg.restart_required ? (
        <p className="config-banner">Application restart required before the module becomes available.</p>
      ) : null}

      <section className="config-panel">
        <h2 className="config-panel-title">Overview</h2>
        <div className="config-stat-grid">
          <div><span className="config-stat-label">State</span><strong>{packageStateLabel(pkg.package_state)}</strong></div>
          <div><span className="config-stat-label">Publisher</span><strong>{pkg.publisher}</strong></div>
          <div><span className="config-stat-label">Installed version</span><strong>{pkg.installed_version}</strong></div>
          <div><span className="config-stat-label">Runtime version</span><strong>{pkg.runtime_version ?? "—"}</strong></div>
        </div>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Trust / Publisher</h2>
        <div className="config-stat-grid">
          <div><span className="config-stat-label">Signed</span><strong>{trustBadgeLabel("signed", pkg.signed)}</strong></div>
          <div><span className="config-stat-label">Signature</span><strong>{trustBadgeLabel("signature_valid", pkg.signature_valid)}</strong></div>
          <div><span className="config-stat-label">Publisher trust</span><strong>{trustBadgeLabel("publisher_trusted", pkg.publisher_trusted)}</strong></div>
          <div><span className="config-stat-label">Publisher status</span><strong>{pkg.publisher_status}</strong></div>
        </div>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Permissions</h2>
        <ul>{Array.isArray(meta.permissions) ? meta.permissions.map((perm) => <li key={String(perm)}>{String(perm)}</li>) : <li>—</li>}</ul>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Capabilities</h2>
        <p>Provides: {Array.isArray(meta.provided_capabilities) ? meta.provided_capabilities.join(", ") : "—"}</p>
        <p>Requires: {Array.isArray(meta.required_capabilities) ? meta.required_capabilities.join(", ") : "—"}</p>
        <p>Optional: {Array.isArray(meta.optional_capabilities) ? meta.optional_capabilities.join(", ") : "—"}</p>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Dependencies</h2>
        <ul>
          {Array.isArray(meta.module_dependencies)
            ? meta.module_dependencies.map((dep) => {
                const item = dep as { module_id?: string; version_range?: string };
                return <li key={`${item.module_id}:${item.version_range}`}>{item.module_id} {item.version_range}</li>;
              })
            : <li>—</li>}
        </ul>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Sites</h2>
        <table className="config-table">
          <thead><tr><th>Site</th><th>Enabled</th><th>Runtime</th><th>Runtime version</th></tr></thead>
          <tbody>
            {sites.map((site) => (
              <tr key={site.site_slug}>
                <td>{site.site_name}</td>
                <td>{site.enabled ? "Ja" : "Nej"}</td>
                <td>{site.runtime_status ?? "—"}</td>
                <td>{site.runtime_version ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Link href={`/config/modules-devices/modules/${encodeURIComponent(moduleId)}`} className="config-button">
          Konfigurera / aktivera i Module Manager
        </Link>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Runtime / Version</h2>
        {pkg.version_match === false ? (
          <p className="config-error">Installed: {pkg.installed_version} · Runtime: {pkg.runtime_version ?? "unknown"} — restart required</p>
        ) : null}
        {pkg.checksum_match === false ? (
          <p className="config-error">Runtime package differs from installed package checksum.</p>
        ) : null}
        <p>Installed checksum: {pkg.checksum_sha256.slice(0, 16)}…</p>
        <p>Runtime checksum: {pkg.runtime_checksum ? `${pkg.runtime_checksum.slice(0, 16)}…` : "—"}</p>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Diagnostics</h2>
        <p>Signature status: {pkg.signature_status}</p>
        {meta.quarantine_reason ? <p>Quarantine reason: {String(meta.quarantine_reason)}</p> : null}
        {meta.quarantined_at ? <p>Detected at: {String(meta.quarantined_at)}</p> : null}
        {meta.detected_version ? <p>Detected version: {String(meta.detected_version)}</p> : null}
        {meta.last_error ? <p>Last error: {String(meta.last_error)}</p> : null}
        <p className="muted">Historical telemetry will be retained if package is removed.</p>
      </section>

      <section className="config-panel">
        <h2 className="config-panel-title">Actions</h2>
        {pkg.rollback_version ? (
          <>
            <button type="button" className="config-button" disabled={busy || quarantined} onClick={() => void prepareRollback()}>
              Rollback to {pkg.rollback_version}
            </button>
            {showRollbackConfirm && rollbackImpact ? (
              <div data-testid="rollback-impact-preview">
                <p>Capabilities removed: {rollbackImpact.capabilities_removed.join(", ") || "—"}</p>
                <p>Affected sites: {rollbackImpact.affected_sites.join(", ") || "—"}</p>
                {rollbackImpact.restart_required ? <p className="config-banner">Omstart krävs efter rollback.</p> : null}
                <button type="button" className="config-button" disabled={busy} onClick={() => void runRollback()}>Bekräfta rollback</button>
              </div>
            ) : null}
          </>
        ) : null}
        <Link href={`/config/modules-devices/store/upload?update=${encodeURIComponent(moduleId)}`} className="config-button">
          Update package
        </Link>
        <button type="button" className="config-button danger" disabled={busy || quarantined} onClick={() => void runRemove()}>
          Remove package
        </button>
        {quarantined ? <p className="config-error">{packageErrorLabel("PACKAGE_QUARANTINED")}</p> : null}
      </section>
    </div>
  );
}
