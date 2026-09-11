"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchStoreCatalog, fetchStoreStatus, type StoreCatalogResponse, type StoreStatusResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleCard } from "@/components/modules-devices/store/ModuleCard";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";

export function CategoryBrowseView({ category }: { category?: string }) {
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
        fetchStoreCatalog({ page_size: 100, category, sort: "name" }),
        fetchStoreStatus(),
      ]);
      setCatalog(cat);
      setStatus(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, [category]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell status={status}>
        <h2 className="config-panel-title">{category ?? "Browse categories"}</h2>
        {error ? <p className="config-error">{error}</p> : null}
        {!category && catalog ? (
          <div className="store-category-chips">
            {catalog.categories.map((c) => (
              <Link
                key={c.id}
                href={`/config/modules-devices/store/categories/${encodeURIComponent(c.id)}`}
                className="config-badge"
              >
                {c.label} ({c.count})
              </Link>
            ))}
          </div>
        ) : null}
        {category ? (
          <div className="store-card-grid">
            {(catalog?.modules ?? []).map((m) => (
              <ModuleCard key={m.module_id} module={m} />
            ))}
          </div>
        ) : null}
      </ModuleStoreShell>
    </>
  );
}
