"use client";

import { createUseSectionFromHash } from "@/lib/useSectionFromHash";
import {
  navigateVehicleSection,
  readVehicleSectionFromLocation,
  type VehicleSectionId,
} from "./vehicleSection";

export const useVehicleSection = createUseSectionFromHash<VehicleSectionId>(
  readVehicleSectionFromLocation,
  navigateVehicleSection,
);
