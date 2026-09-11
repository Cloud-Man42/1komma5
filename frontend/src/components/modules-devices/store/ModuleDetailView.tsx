"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchStoreModuleDetail, type StoreModuleDetailResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";
import { SafeText } from "@/components/modules-devices/store/SafeMarkdown";
import {
  isActionable,
  originLabel,
  primaryActionLabel,
  securityBadgeClass,
  trustBadgeClass,
} from "@/components/modules-devices/store/storeLabels";

type TabId = "overview" | "capabilities" | "permissions" | "compatibility" | "security";

export function ModuleDetailView({ moduleId }: { moduleId: string }) {
  const [detail, setDetail] = useState<StoreModuleDetailResponse | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    try {
      setDetail(await fetchStoreModuleDetail(moduleId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load module");
    }
  }, [moduleId]);

  useEffect(() => {
    void load();
  }, [load]);

  const s = detail?.summary;

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell>
        {error ? <p className="config-error">{error}</p> : null}
        {s ? (
          <>
            <section className="config-panel store-hero" data-testid="module-detail-hero">
              <div className="config-panel-header">
                <div>
                  <h2 className="config-page-title">
                    <SafeText text={s.display_name} />
                  </h2>
                  <p className="muted">
                    {s.publisher_name} · {s.category} · {originLabel(s.origin)}
                  </p>
                </div>
                <div className="store-card-badges">
                  <span className={trustBadgeClass(s.trust_badge)}>{s.trust_badge}</span>
                  <span className={securityBadgeClass(s.security_badge)}>{s.security_badge.replace(/_/g, " ")}</span>
                </div>
              </div>
              <p>
                <SafeText text={detail.long_description || s.description} />
              </p>
              <div className="config-stat-grid">
                <div>
                  <span className="config-stat-label">Installed</span>
                  <strong>{s.installed_version ?? "Not installed"}</strong>
                </div>
                <div>
                  <span className="config-stat-label">Latest</span>
                  <strong>{s.latest_version ?? "—"}</strong>
                </div>
                <div>
                  <span className="config-stat-label">Action</span>
                  <strong>{primaryActionLabel(s.primary_action)}</strong>
                </div>
              </div>
              {s.control_capable ? (
                <p className="config-banner" data-testid="control-warning">
                  This module can issue commands to physical equipment. Runtime execution is currently blocked until
                  the control-module isolation gate has been approved.
                </p>
              ) : null}
              {s.policy.decision === "DENY" || s.primary_action === "BLOCKED_BY_POLICY" ? (
                <p className="config-error">{s.policy.explanation}</p>
              ) : null}
              <div className="store-card-actions">
                {isActionable(s.primary_action) ? (
                  <Link
                    href={`/config/modules-devices/store/${encodeURIComponent(moduleId)}/install`}
                    className="config-button primary"
                  >
                    {primaryActionLabel(s.primary_action)}
                  </Link>
                ) : (
                  <span className="config-badge">{primaryActionLabel(s.primary_action)}</span>
                )}
              </div>
            </section>
            <nav className="config-subnav">
              {(["overview", "capabilities", "permissions", "compatibility", "security"] as TabId[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={tab === t ? "config-subnav-link active" : "config-subnav-link"}
                  onClick={() => setTab(t)}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </nav>
            {tab === "overview" && detail.features.length > 0 ? (
              <section className="config-panel">
                <h3>What this module enables</h3>
                <ul>
                  {detail.features.map((f) => (
                    <li key={f.feature_id}>
                      <strong>{f.feature_name}</strong>
                      {f.description ? ` — ${f.description}` : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {tab === "capabilities" ? (
              <section className="config-panel">
                <ul>
                  {detail.capabilities.map((c) => (
                    <li key={c.capability}>{c.label}</li>
                  ))}
                </ul>
              </section>
            ) : null}
            {tab === "permissions" ? (
              <section className="config-panel">
                {detail.permissions.map((p) => (
                  <div key={p.permission} className="store-permission-row" data-testid={`perm-${p.permission}`}>
                    <strong>{p.label}</strong>
                    <span className={p.risk_level === "CRITICAL" || p.risk_level === "HIGH" ? "config-badge danger" : "config-badge"}>
                      {p.risk_level}
                    </span>
                    <span className="muted">{p.group}</span>
                  </div>
                ))}
              </section>
            ) : null}
            {tab === "compatibility" ? (
              <section className="config-panel">
                <p>{detail.compatibility.compatible ? "Compatible with this EMIC installation" : "Not compatible"}</p>
                <p>EMIC version: {detail.compatibility.emic_version}</p>
                {detail.compatibility.reasons.map((r) => (
                  <p key={r} className="config-error">
                    {r}
                  </p>
                ))}
              </section>
            ) : null}
            {tab === "security" ? (
              <section className="config-panel" data-testid="security-tab">
                <p>Decision: {String(detail.security.security_decision ?? s.policy.decision)}</p>
                <p>{s.policy.explanation}</p>
                <p>{String(detail.security.runtime_message ?? "")}</p>
              </section>
            ) : null}
          </>
        ) : null}
      </ModuleStoreShell>
    </>
  );
}
