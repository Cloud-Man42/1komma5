"use client";

import { useCallback, useEffect, useState } from "react";
import {
  navigateVehicleSection,
  readVehicleSectionFromLocation,
  type VehicleSectionId,
} from "./vehicleSection";

export function useVehicleSection() {
  const [section, setSection] = useState<VehicleSectionId>(() => readVehicleSectionFromLocation());

  useEffect(() => {
    const sync = () => setSection(readVehicleSectionFromLocation());
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  const navigate = useCallback((next: VehicleSectionId, slug: string) => {
    navigateVehicleSection(slug, next);
    setSection(next);
  }, []);

  return { section, navigate };
}
