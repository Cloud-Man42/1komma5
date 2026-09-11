"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchStoreSecurityCenter, fetchStoreStatus, type StoreStatusResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";

export function SecurityCenterView() {
  const [center, setCenter] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<StoreStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    try {
      const [c, st] = await Promise.all([fetchStoreSecurityCenter(), fetchStoreStatus()]);
      setCenter(c);
      setStatus(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const cards = [
    { label: "Installed modules", value: center?.installed_count, href: "/config/modules-devices/store/installed" },
    { label: "Updates available", value: center?.updates_available, href: "/config/modules-devices/store/updates" },
    { label: "Security reviews", value: center?.security_reviews_required, href: "/config/modules-devices/store?security=SECURITY_REVIEW_REQUIRED" },
    { label: "Critical issues", value: center?.critical_issues, href: "/config/modules-devices/store/security" },
    { label: "Quarantined", value: center?.quarantined_count, href: "/config/modules-devices/store/security" },
  ];

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell status={status}>
        <h2 className="config-panel-title">Marketplace Security</h2>
        {error ? <p className="config-error">{error}</p> : null}
        <div className="config-stat-grid">
          {cards.map((c) => (
            <Link key={c.label} href={c.href} className="config-panel store-stat-card">
              <span className="config-stat-label">{c.label}</span>
              <strong>{String(c.value ?? 0)}</strong>
            </Link>
          ))}
        </div>
        {Array.isArray(center?.revoked_publishers) && (center.revoked_publishers as string[]).length > 0 ? (
          <section className="config-panel">
            <h3>Revoked publishers</h3>
            <ul>
              {(center.revoked_publishers as string[]).map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </section>
        ) : (
          <p className="muted">No revoked publishers.</p>
        )}
        {Array.isArray(center?.quarantined) && (center.quarantined as unknown[]).length > 0 ? (
          <section className="config-panel">
            <h3>Quarantined artifacts</h3>
            <ul>
              {(center.quarantined as Array<Record<string, string>>).map((q) => (
                <li key={`${q.module_id}-${q.version}`}>
                  {q.module_id} v{q.version} — {q.reason}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </ModuleStoreShell>
    </>
  );
}
