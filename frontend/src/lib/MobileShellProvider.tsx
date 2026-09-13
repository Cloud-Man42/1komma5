"use client";

import { createContext, useContext, useMemo } from "react";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import { useMobileSummary } from "@/lib/useMobileSummary";

interface MobileShellContextValue {
  freshnessLabel: string | null;
}

const MobileShellContext = createContext<MobileShellContextValue>({ freshnessLabel: null });

export function MobileShellProvider({ children }: { children: React.ReactNode }) {
  const { selectedSlugs, accessibleSites, loading } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const { data } = useMobileSummary(loading ? [] : slugs);

  const value = useMemo(
    () => ({ freshnessLabel: data?.freshnessLabel ?? null }),
    [data?.freshnessLabel],
  );

  return <MobileShellContext.Provider value={value}>{children}</MobileShellContext.Provider>;
}

export function useMobileShellContext(): MobileShellContextValue {
  return useContext(MobileShellContext);
}
