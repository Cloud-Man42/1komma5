"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchStoreCatalog, fetchStoreStatus, type StoreCatalogResponse, type StoreStatusResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleCard } from "@/components/modules-devices/store/ModuleCard";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";

export function UpdatesView() {
  const [catalog, setCatalog] = useState<StoreCatalogResponse | null>(null);
  const [status, setStatus] = useState<StoreStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    try {
      const [cat, st] = await Promise.all([
        fetchStoreCatalog({ update_available: true, page_size: 100 }),
        fetchStoreStatus(),
      ]);
      setCatalog(cat);
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
        <h2 className="config-panel-title">Available updates</h2>
        {error ? <p className="config-error">{error}</p> : null}
        {catalog?.modules.length === 0 ? <p className="muted">No updates available.</p> : null}
        <div className="store-card-grid">
          {(catalog?.modules ?? []).map((m) => (
            <ModuleCard key={m.module_id} module={m} />
          ))}
        </div>
      </ModuleStoreShell>
    </>
  );
}
