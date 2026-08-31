"use client";

import { useCallback, useEffect, useState } from "react";
import { subscribeToHashNavigation } from "@/lib/hashSectionNavigation";

export function createUseSectionFromHash<T>(
  readSectionFromLocation: () => T,
  navigateSection?: (slug: string, section: T) => void,
) {
  return function useSectionFromHash(): { section: T; navigate?: (next: T, slug: string) => void } {
    const [section, setSection] = useState<T>(() => readSectionFromLocation());

    useEffect(() => {
      const sync = () => setSection(readSectionFromLocation());
      sync();
      return subscribeToHashNavigation(sync);
    }, []);

    const navigate = navigateSection
      ? useCallback(
          (next: T, slug: string) => {
            navigateSection(slug, next);
            setSection(next);
          },
          [],
        )
      : undefined;

    return navigate ? { section, navigate } : { section };
  };
}
