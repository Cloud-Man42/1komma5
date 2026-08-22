"use client";

import { useEffect } from "react";
import { hydrateEnergySceneConfig } from "@/lib/energySceneConfigStore";

export function EnergySceneConfigProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    void hydrateEnergySceneConfig();
  }, []);

  return children;
}
