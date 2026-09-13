"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearTenantScopedStorage, fetchMyTenants, selectTenant, type TenantSummary } from "@/lib/tenantApi";

type TenantContextValue = {
  tenants: TenantSummary[];
  currentTenant: TenantSummary | null;
  loading: boolean;
  switchTenant: (tenantId: number) => Promise<void>;
  refreshTenants: () => Promise<void>;
};

const TenantSelectionContext = createContext<TenantContextValue | null>(null);

export function TenantSelectionProvider({ children }: { children: React.ReactNode }) {
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [currentTenant, setCurrentTenant] = useState<TenantSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshTenants = useCallback(async () => {
    setLoading(true);
    try {
      const list = await fetchMyTenants();
      setTenants(list);
      if (list.length === 1) {
        setCurrentTenant(list[0]);
      }
    } catch {
      setTenants([]);
      setCurrentTenant(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshTenants();
  }, [refreshTenants]);

  const switchTenant = useCallback(
    async (tenantId: number) => {
      const previous = currentTenant?.id ?? null;
      clearTenantScopedStorage(previous);
      const tenant = await selectTenant(tenantId);
      setCurrentTenant(tenant);
      window.location.reload();
    },
    [currentTenant],
  );

  const value = useMemo(
    () => ({ tenants, currentTenant, loading, switchTenant, refreshTenants }),
    [tenants, currentTenant, loading, switchTenant, refreshTenants],
  );

  return <TenantSelectionContext.Provider value={value}>{children}</TenantSelectionContext.Provider>;
}

export function useTenantSelection() {
  const ctx = useContext(TenantSelectionContext);
  if (!ctx) {
    throw new Error("useTenantSelection must be used within TenantSelectionProvider");
  }
  return ctx;
}
