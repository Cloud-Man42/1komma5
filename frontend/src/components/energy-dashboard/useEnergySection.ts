"use client";

import { useEffect, useState } from "react";
import { readEnergySectionFromLocation, type EnergySectionId } from "./energySection";

export function useEnergySection(): { section: EnergySectionId } {
  const [section, setSection] = useState<EnergySectionId>("flow");

  useEffect(() => {
    const update = () => setSection(readEnergySectionFromLocation());
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
