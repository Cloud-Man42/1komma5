"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchStoreCatalog, fetchStoreStatus, type StoreCatalogResponse, type StoreStatusResponse } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleCard } from "@/components/modules-devices/store/ModuleCard";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";

export function DiscoverView() {
  const [catalog, setCatalog] = useState<StoreCatalogResponse | null>(null);
  const [status, setStatus] = useState<StoreStatusResponse | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (q?: string) => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      setLoading(false);
      return;
    }
    setError(null);
    try {
      const [cat, st] = await Promise.all([
        fetchStoreCatalog({ page_size: 48, search: q || undefined, sort: "recommended" }),
        fetchStoreStatus(),
      ]);
      setCatalog(cat);
      setStatus(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load store");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const official = catalog?.modules.filter((m) => m.trust_tier === "OFFICIAL") ?? [];
  const featured = catalog?.modules.filter((m) => m.origin === "BUILT_IN").slice(0, 6) ?? [];

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell status={status}>
        {error ? <p className="config-error">{error}</p> : null}
        <section className="store-search-bar">
          <input
            type="search"
            className="config-input"
            placeholder="Search modules, publishers, capabilities…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load(search);
            }}
            data-testid="store-search-input"
          />
          <button type="button" className="config-button" onClick={() => void load(search)}>
            Search
          </button>
        </section>
        {loading ? <p className="muted">Loading catalog…</p> : null}
        {!loading && catalog && catalog.categories.length > 0 ? (
          <section className="store-section">
            <h2 className="config-panel-title">Categories</h2>
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
          </section>
        ) : null}
        {featured.length > 0 ? (
          <section className="store-section">
            <h2 className="config-panel-title">Official EMIC Modules</h2>
            <div className="store-card-grid">
              {featured.map((m) => (
                <ModuleCard key={m.module_id} module={m} />
              ))}
            </div>
          </section>
        ) : null}
        <section className="store-section">
          <h2 className="config-panel-title">All modules</h2>
          {catalog?.modules.length === 0 ? <p className="muted">No modules found.</p> : null}
          <div className="store-card-grid">
            {(catalog?.modules ?? []).map((m) => (
              <ModuleCard key={m.module_id} module={m} />
            ))}
          </div>
        </section>
      </ModuleStoreShell>
    </>
  );
}
