"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchSiteSelection, patchSiteSelection } from "@/lib/multiSiteApi";
import { fetchSites, type Site } from "@/lib/api";

interface SiteSelectionContextValue {
  loading: boolean;
  accessibleSites: Site[];
  selectedSlugs: string[];
  draftSlugs: string[];
  setDraftSlugs: (slugs: string[]) => void;
  selectAll: () => void;
  clearAll: () => void;
  toggleDraft: (slug: string) => void;
  applySelection: (options?: { pathname?: string }) => Promise<void>;
  refresh: () => Promise<void>;
}

const SiteSelectionContext = createContext<SiteSelectionContextValue | null>(null);

function preservePath(pathname: string, fromSlug: string, toSlug: string): string {
  const marker = `/sites/${fromSlug}`;
  if (pathname.includes(marker)) {
    return pathname.replace(marker, `/sites/${toSlug}`);
  }
  return `/sites/${toSlug}`;
}

export function SiteSelectionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [accessibleSites, setAccessibleSites] = useState<Site[]>([]);
  const [selectedSlugs, setSelectedSlugs] = useState<string[]>([]);
  const [draftSlugs, setDraftSlugs] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [sites, selection] = await Promise.all([fetchSites(), fetchSiteSelection()]);
      setAccessibleSites(sites);
      const slugs = selection.selectedSiteSlugs.length ? selection.selectedSiteSlugs : sites.map((s) => s.slug);
      setSelectedSlugs(slugs);
      setDraftSlugs(slugs);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selectAll = useCallback(() => {
    setDraftSlugs(accessibleSites.map((s) => s.slug));
  }, [accessibleSites]);

  const clearAll = useCallback(() => {
    setDraftSlugs([]);
  }, []);

  const toggleDraft = useCallback((slug: string) => {
    setDraftSlugs((prev) => (prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]));
  }, []);

  const applySelection = useCallback(
    async (options?: { pathname?: string }) => {
      const unique = [...new Set(draftSlugs)];
      const saved = await patchSiteSelection(unique);
      setSelectedSlugs(saved.selectedSiteSlugs);
      setDraftSlugs(saved.selectedSiteSlugs);

      if (saved.selectedSiteSlugs.length === 0) {
        router.push("/");
        return;
      }
      if (saved.selectedSiteSlugs.length === 1) {
        const slug = saved.selectedSiteSlugs[0];
        const path = options?.pathname
          ? preservePath(options.pathname, selectedSlugs[0] ?? slug, slug)
          : `/sites/${slug}`;
        router.push(path);
        return;
      }
      router.push("/overview");
    },
    [draftSlugs, router, selectedSlugs],
  );

  const value = useMemo(
    () => ({
      loading,
      accessibleSites,
      selectedSlugs,
      draftSlugs,
      setDraftSlugs,
      selectAll,
      clearAll,
      toggleDraft,
      applySelection,
      refresh,
    }),
    [
      loading,
      accessibleSites,
      selectedSlugs,
      draftSlugs,
      selectAll,
      clearAll,
      toggleDraft,
      applySelection,
      refresh,
    ],
  );

  return <SiteSelectionContext.Provider value={value}>{children}</SiteSelectionContext.Provider>;
}

export function useSiteSelection(): SiteSelectionContextValue {
  const ctx = useContext(SiteSelectionContext);
  if (!ctx) throw new Error("useSiteSelection must be used within SiteSelectionProvider");
  return ctx;
}
