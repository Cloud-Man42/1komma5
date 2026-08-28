"use client";

import { ReactNode, createContext, useContext } from "react";
import { SiteDashboard } from "@/lib/api";
import { useSiteDashboard as useSiteDashboardHook } from "@/lib/useSiteDashboard";

interface SiteDataContextValue {
  dashboard: SiteDashboard | null;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
}

const SiteDataContext = createContext<SiteDataContextValue | null>(null);

export function SiteDataProvider({
  slug,
  refreshSeconds = 60,
  children,
}: {
  slug: string;
  refreshSeconds?: number;
  children: ReactNode;
}) {
  const value = useSiteDashboardHook(slug, refreshSeconds);
  return <SiteDataContext.Provider value={value}>{children}</SiteDataContext.Provider>;
}

export function useSiteData(): SiteDataContextValue {
  const ctx = useContext(SiteDataContext);
  if (ctx === null) {
    throw new Error("useSiteData must be used within SiteDataProvider");
  }
  return ctx;
}

export function useOptionalSiteData(): SiteDataContextValue | null {
  return useContext(SiteDataContext);
}
