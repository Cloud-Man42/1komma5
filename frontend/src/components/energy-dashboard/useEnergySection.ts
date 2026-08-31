"use client";

import { createUseSectionFromHash } from "@/lib/useSectionFromHash";
import { readEnergySectionFromLocation, type EnergySectionId } from "./energySection";

export const useEnergySection = createUseSectionFromHash<EnergySectionId>(readEnergySectionFromLocation);
