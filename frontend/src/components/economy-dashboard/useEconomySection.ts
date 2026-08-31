"use client";

import { createUseSectionFromHash } from "@/lib/useSectionFromHash";
import { readEconomySectionFromLocation, type EconomySectionId } from "./economySection";

export const useEconomySection = createUseSectionFromHash<EconomySectionId>(
  readEconomySectionFromLocation,
);
