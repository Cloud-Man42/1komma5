"use client";

import { ReactNode, createContext, useContext } from "react";
import type { SolarSiteConfig, SolarWeather } from "@/lib/api";

interface SolarLayoutContextValue {
  config: SolarSiteConfig | null;
  weather: SolarWeather | null;
}

const SolarLayoutContext = createContext<SolarLayoutContextValue | null>(null);

export function SolarLayoutProvider({
  config,
  weather,
  children,
}: {
  config: SolarSiteConfig | null;
  weather: SolarWeather | null;
  children: ReactNode;
}) {
  return (
    <SolarLayoutContext.Provider value={{ config, weather }}>{children}</SolarLayoutContext.Provider>
  );
}

export function useSolarLayoutData(): SolarLayoutContextValue | null {
  return useContext(SolarLayoutContext);
}
