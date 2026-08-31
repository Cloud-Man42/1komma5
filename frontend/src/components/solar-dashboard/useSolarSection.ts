"use client";

import { createUseSectionFromHash } from "@/lib/useSectionFromHash";
import { readSolarSectionFromLocation, type SolarSectionId } from "./solarSection";

export const useSolarSection = createUseSectionFromHash<SolarSectionId>(readSolarSectionFromLocation);
