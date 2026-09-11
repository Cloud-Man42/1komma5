"use client";

import { packageErrorLabel, trustBadgeLabel } from "@/components/modules-devices/packageErrorLabels";
import type { PackageImpactResult, PackageValidationResult } from "@/lib/api";

type Props = {
  validation: PackageValidationResult;
  impact: PackageImpactResult | null;
  installedVersion?: string | null;
  mode?: "install" | "update";
};

export function PackageReviewPanel({ validation, impact, installedVersion, mode = "install" }: Props) {
  return (
    <section className="config-panel" data-testid="package-review-panel">
      <h2 className="config-panel-title">Granskningsresultat</h2>
      {validation.errors.map((code) => (
        <p key={code} className="config-error">{packageErrorLabel(code)}</p>
      ))}
      {validation.warnings.map((warning) => (
        <p key={warning} className="config-banner">{warning}</p>
      ))}
      <div className="config-stat-grid">
        <div><span className="config-stat-label">Modul</span><strong>{validation.manifest?.name ?? "—"}</strong></div>
        <div><span className="config-stat-label">Version</span><strong>{validation.manifest?.version ?? "—"}</strong></div>
        <div><span className="config-stat-label">Publisher</span><strong>{validation.manifest?.publisher ?? "—"}</strong></div>
      </div>
      {mode === "update" && installedVersion ? (
        <p className="muted">Installerad: {installedVersion} → Ny: {validation.manifest?.version ?? "—"}</p>
      ) : null}
      <div className="config-stat-grid">
        <div><span className="config-stat-label">Signed</span><strong>{trustBadgeLabel("signed", validation.signed)}</strong></div>
        <div><span className="config-stat-label">Signature</span><strong>{trustBadgeLabel("signature_valid", validation.signature_valid)}</strong></div>
        <div><span className="config-stat-label">Publisher trust</span><strong>{trustBadgeLabel("publisher_trusted", validation.publisher_trusted)}</strong></div>
        <div><span className="config-stat-label">Install</span><strong>{trustBadgeLabel("install_allowed", validation.install_allowed)}</strong></div>
      </div>
      <h3>Permissions</h3>
      <ul>{validation.permissions.map((perm) => <li key={perm}>{perm}</li>)}</ul>
      {validation.permissions.some((perm) => perm.includes("control")) ? (
        <p className="config-banner">This module can control physical devices.</p>
      ) : null}
      <h3>Capabilities</h3>
      <p>Provides: {validation.provided_capabilities.join(", ") || "—"}</p>
      <p>Requires: {validation.required_capabilities.join(", ") || "—"}</p>
      <p>Optional: {validation.optional_capabilities.join(", ") || "—"}</p>
      <h3>Dependencies</h3>
      <ul>
        {validation.module_dependencies.map((dep) => (
          <li key={`${dep.module_id}:${dep.version_range}`}>{dep.module_id} {dep.version_range}</li>
        ))}
      </ul>
      {impact ? (
        <>
          <h3>Impact</h3>
          <p>Affected sites: {impact.affected_sites.join(", ") || "—"}</p>
          <p>Affected devices: {impact.affected_devices.join(", ") || "—"}</p>
          <p>Capabilities added: {impact.capabilities_added.join(", ") || "—"}</p>
          <p>Capabilities removed: {impact.capabilities_removed.join(", ") || "—"}</p>
          {impact.restart_required ? <p className="config-banner">Omstart krävs efter installation.</p> : null}
        </>
      ) : null}
      <p className="muted">Permissions valideras vid install men isolerar inte modulen på OS-nivå.</p>
    </section>
  );
}
