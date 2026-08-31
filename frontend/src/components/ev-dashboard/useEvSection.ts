"use client";

import { createUseSectionFromHash } from "@/lib/useSectionFromHash";
import { readEvSectionFromLocation, type EvSectionId } from "./evSection";

export const useEvSection = createUseSectionFromHash<EvSectionId>(readEvSectionFromLocation);
