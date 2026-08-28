"use client";

import { useEffect, useState } from "react";
import { readEvSectionFromLocation, type EvSectionId } from "./evSection";

export function useEvSection(): { section: EvSectionId } {
  const [section, setSection] = useState<EvSectionId>("overview");

  useEffect(() => {
    const update = () => setSection(readEvSectionFromLocation());
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
