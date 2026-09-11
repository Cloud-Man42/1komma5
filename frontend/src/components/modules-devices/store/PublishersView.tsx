"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchStorePublishers, fetchStoreStatus, type StoreStatusResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";
import { trustBadgeClass } from "@/components/modules-devices/store/storeLabels";

export function PublishersView() {
  const [publishers, setPublishers] = useState<
    Array<{ publisher_id: string; display_name: string; tier: string; status: string; module_count: number }>
  >([]);
  const [status, setStatus] = useState<StoreStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    try {
      const [pubs, st] = await Promise.all([fetchStorePublishers(), fetchStoreStatus()]);
      setPublishers(pubs);
      setStatus(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell status={status}>
        <h2 className="config-panel-title">Publishers</h2>
        {error ? <p className="config-error">{error}</p> : null}
        <div className="store-card-grid">
          {publishers.map((p) => (
            <Link
              key={p.publisher_id}
              href={`/config/modules-devices/store/publishers/${encodeURIComponent(p.publisher_id)}`}
              className="config-panel store-publisher-card"
            >
              <h3>{p.display_name}</h3>
              <p className="muted">{p.publisher_id}</p>
              <span className={trustBadgeClass(p.tier)}>{p.tier}</span>
              <p>{p.module_count} modules · {p.status}</p>
            </Link>
          ))}
        </div>
      </ModuleStoreShell>
    </>
  );
}

export function PublisherDetailView({ publisherId }: { publisherId: string }) {
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    import("@/lib/api")
      .then(({ fetchStorePublisher }) => fetchStorePublisher(publisherId))
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [publisherId]);

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell>
        {error ? <p className="config-error">{error}</p> : null}
        {detail ? (
          <article className="config-panel">
            <h2>{String(detail.display_name)}</h2>
            <p className="muted">{String(detail.publisher_id)}</p>
            <p>Tier: {String(detail.tier)} · Status: {String(detail.status)}</p>
            {detail.verified_domain ? <p>Verified domain: {String(detail.verified_domain)}</p> : null}
            <h3>Modules</h3>
            <ul>
              {((detail.modules as string[]) ?? []).map((m) => (
                <li key={m}>
                  <Link href={`/config/modules-devices/store/${encodeURIComponent(m)}`}>{m}</Link>
                </li>
              ))}
            </ul>
          </article>
        ) : null}
      </ModuleStoreShell>
    </>
  );
}
