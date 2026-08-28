"use client";

import { ReactNode, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { DashboardShell } from "@/components/intelligence-dashboard/DashboardShell";
import { SiteDataProvider, useSiteData } from "@/lib/SiteDataProvider";
import {
  fetchSolarConfig,
  fetchSolarWeather,
  type SolarSiteConfig,
  type SolarWeather,
} from "@/lib/api";

function SiteLayoutInner({ children }: { children: ReactNode }) {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { dashboard } = useSiteData();
  const [config, setConfig] = useState<SolarSiteConfig | null>(null);
  const [weather, setWeather] = useState<SolarWeather | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      const cfg = await fetchSolarConfig(slug).catch(() => null);
      if (!active) return;
      setConfig(cfg);
      if (!cfg?.enabled) {
        setWeather(null);
        return;
      }
      const wx = await fetchSolarWeather(slug).catch(() => null);
      if (active) setWeather(wx);
    };

    load();
    const interval = setInterval(load, 300_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug]);

  return (
    <DashboardShell
      slug={slug}
      dashboard={dashboard}
      latitude={config?.latitude}
      longitude={config?.longitude}
      weather={weather}
    >
      {children}
    </DashboardShell>
  );
}

export default function SiteLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ slug: string }>();
  return (
    <SiteDataProvider slug={params.slug} refreshSeconds={30}>
      <SiteLayoutInner>{children}</SiteLayoutInner>
    </SiteDataProvider>
  );
}
