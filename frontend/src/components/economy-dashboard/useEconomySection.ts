"use client";

import { useEffect, useState } from "react";
import { readEconomySectionFromLocation, type EconomySectionId } from "./economySection";

export function useEconomySection(): { section: EconomySectionId } {
  const [section, setSection] = useState<EconomySectionId>("analysis");

  useEffect(() => {
    const update = () => setSection(readEconomySectionFromLocation());
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, []);

  return { section };
}
