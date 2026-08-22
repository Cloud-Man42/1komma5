import {
  clonePaths,
  deriveEquipment,
  loadInitialPaths,
  parseStoredPaths,
  type CalibratorPaths,
} from "./energySceneCalibrator";
import {
  DEFAULT_EQUIPMENT_VARIANTS,
  type EquipmentVariants,
  isBatteryVariantId,
  isInverterVariantId,
  isSolarVariantId,
} from "./energySceneEquipment";
import { DEFAULT_SCENE_PHOTO, isCustomPhotoUrl } from "./energyScenePhoto";
import { WIRE_SLOT_FLOW, type WireAnimationSlot } from "./energyFlow";
import { orientPathBetween, pointsToPath, type SceneWireId } from "./energyFlowSceneLayout";

export const SCENE_CONFIG_STORAGE_KEY = "energy-scene-v2";
/** @deprecated Legacy prefix kept for one-time migration. */
export const SCENE_CONFIG_STORAGE_PREFIX = "energy-scene-config:";
export const SHARED_SCENE_SITE_SLUG = "default";
export const SCENE_CONFIG_UPDATED_EVENT = "energy-scene-config-updated";

export type SceneConfig = {
  photoUrl: string;
  paths: CalibratorPaths;
  equipment: EquipmentVariants;
  /** When false, equipment SVG overlays are hidden (photo may already show gear). */
  showEquipmentOverlay: boolean;
  updatedAt: string;
};

export type PersistedSceneConfig = {
  photoSource: "default" | "custom";
  photoUrl?: string;
  paths: CalibratorPaths;
  equipment: EquipmentVariants;
  showEquipmentOverlay: boolean;
  updatedAt: string;
};

/** @deprecated Use SCENE_CONFIG_STORAGE_KEY. */
export function sceneConfigStorageKey(siteSlug = "default"): string {
  return `${SCENE_CONFIG_STORAGE_PREFIX}${siteSlug}`;
}

export function createDefaultSceneConfig(): SceneConfig {
  return {
    photoUrl: DEFAULT_SCENE_PHOTO,
    paths: loadInitialPaths(),
    equipment: { ...DEFAULT_EQUIPMENT_VARIANTS },
    showEquipmentOverlay: true,
    updatedAt: new Date().toISOString(),
  };
}

export function parseSceneConfig(raw: string): SceneConfig | null {
  try {
    const parsed = JSON.parse(raw) as Partial<SceneConfig & PersistedSceneConfig>;
    if (!parsed?.paths || !parseStoredPaths(JSON.stringify(parsed.paths))) return null;
    if (!parsed.equipment) return null;

    const equipment = parsed.equipment;
    if (
      !isSolarVariantId(equipment.solar) ||
      !isInverterVariantId(equipment.inverter) ||
      !isBatteryVariantId(equipment.battery)
    ) {
      return null;
    }

    const photoUrl =
      typeof parsed.photoUrl === "string" && parsed.photoUrl.length > 0
        ? parsed.photoUrl
        : parsed.photoSource === "custom"
          ? DEFAULT_SCENE_PHOTO
          : DEFAULT_SCENE_PHOTO;

    return {
      photoUrl,
      paths: clonePaths(parsed.paths as CalibratorPaths),
      equipment: {
        solar: equipment.solar,
        inverter: equipment.inverter,
        battery: equipment.battery,
      },
      showEquipmentOverlay: parsed.showEquipmentOverlay ?? true,
      updatedAt: parsed.updatedAt ?? new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

function parsePersistedSceneConfig(raw: string): PersistedSceneConfig | null {
  const parsed = parseSceneConfig(raw);
  if (!parsed) return null;

  return {
    photoSource: isCustomPhotoUrl(parsed.photoUrl) ? "custom" : "default",
    photoUrl: isCustomPhotoUrl(parsed.photoUrl) ? parsed.photoUrl : undefined,
    paths: parsed.paths,
    equipment: parsed.equipment,
    showEquipmentOverlay: parsed.showEquipmentOverlay,
    updatedAt: parsed.updatedAt,
  };
}

function readLegacyConfigs(): PersistedSceneConfig[] {
  if (typeof window === "undefined") return [];

  const configs: PersistedSceneConfig[] = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (!key?.startsWith(SCENE_CONFIG_STORAGE_PREFIX)) continue;
    const raw = localStorage.getItem(key);
    if (!raw) continue;
    const parsed = parsePersistedSceneConfig(raw);
    if (parsed) configs.push(parsed);
  }
  return configs;
}

export function cleanupLegacySceneStorage(): void {
  if (typeof window === "undefined") return;

  for (let i = localStorage.length - 1; i >= 0; i -= 1) {
    const key = localStorage.key(i);
    if (!key) continue;
    if (key.startsWith(SCENE_CONFIG_STORAGE_PREFIX)) {
      localStorage.removeItem(key);
    }
    if (key === "energy-scene-calibrator-draft") {
      localStorage.removeItem(key);
    }
  }
}

export function readPersistedSceneConfig(): PersistedSceneConfig {
  if (typeof window === "undefined") {
    const defaults = createDefaultSceneConfig();
    return {
      photoSource: "default",
      paths: defaults.paths,
      equipment: defaults.equipment,
      showEquipmentOverlay: defaults.showEquipmentOverlay,
      updatedAt: defaults.updatedAt,
    };
  }

  const currentRaw = localStorage.getItem(SCENE_CONFIG_STORAGE_KEY);
  if (currentRaw) {
    const parsed = parsePersistedSceneConfig(currentRaw);
    if (parsed) return parsed;
  }

  const legacyConfigs = readLegacyConfigs();
  if (legacyConfigs.length > 0) {
    const newest = legacyConfigs.reduce((best, candidate) =>
      candidate.updatedAt > best.updatedAt ? candidate : best,
    );
    writePersistedSceneConfig(newest);
    return newest;
  }

  const defaults = createDefaultSceneConfig();
  return {
    photoSource: "default",
    paths: defaults.paths,
    equipment: defaults.equipment,
    showEquipmentOverlay: defaults.showEquipmentOverlay,
    updatedAt: defaults.updatedAt,
  };
}

export function writePersistedSceneConfig(config: PersistedSceneConfig): void {
  if (typeof window === "undefined") return;

  const payload: PersistedSceneConfig = {
    photoSource: config.photoSource,
    paths: clonePaths(config.paths),
    equipment: { ...config.equipment },
    showEquipmentOverlay: config.showEquipmentOverlay,
    updatedAt: config.updatedAt,
  };

  if (config.photoSource === "custom" && config.photoUrl && isCustomPhotoUrl(config.photoUrl)) {
    payload.photoUrl = config.photoUrl;
  }

  localStorage.setItem(SCENE_CONFIG_STORAGE_KEY, JSON.stringify(payload));
}

/** @deprecated Test helper for legacy slug resolution. */
export function resolveSceneConfig(
  getStored: (siteSlug: string) => string | null,
  knownSlugs: string[] = [],
): SceneConfig {
  const shared = getStored(SHARED_SCENE_SITE_SLUG);
  if (shared) {
    const parsed = parseSceneConfig(shared);
    if (parsed) return parsed;
  }

  let newest: SceneConfig | null = null;
  for (const slug of knownSlugs) {
    if (slug === SHARED_SCENE_SITE_SLUG) continue;
    const raw = getStored(slug);
    if (!raw) continue;
    const parsed = parseSceneConfig(raw);
    if (!parsed) continue;
    if (!newest || parsed.updatedAt > newest.updatedAt) {
      newest = parsed;
    }
  }

  return newest ?? createDefaultSceneConfig();
}

/** @deprecated Use hydrateEnergySceneConfig from energySceneConfigStore. */
export function loadSceneConfig(_siteSlug = SHARED_SCENE_SITE_SLUG): SceneConfig {
  const persisted = readPersistedSceneConfig();
  return {
    photoUrl:
      persisted.photoSource === "custom" && persisted.photoUrl
        ? persisted.photoUrl
        : DEFAULT_SCENE_PHOTO,
    paths: clonePaths(persisted.paths),
    equipment: { ...persisted.equipment },
    showEquipmentOverlay: persisted.showEquipmentOverlay,
    updatedAt: persisted.updatedAt,
  };
}

/** @deprecated Use commitEnergySceneConfig from energySceneConfigStore. */
export function saveSceneConfig(config: SceneConfig, _siteSlug = SHARED_SCENE_SITE_SLUG): void {
  writePersistedSceneConfig({
    photoSource: isCustomPhotoUrl(config.photoUrl) ? "custom" : "default",
    photoUrl: isCustomPhotoUrl(config.photoUrl) ? config.photoUrl : undefined,
    paths: config.paths,
    equipment: config.equipment,
    showEquipmentOverlay: config.showEquipmentOverlay,
    updatedAt: new Date().toISOString(),
  });
  window.dispatchEvent(new CustomEvent(SCENE_CONFIG_UPDATED_EVENT, { detail: config }));
}

export function wirePathFromConfig(paths: CalibratorPaths, id: SceneWireId): string {
  return pointsToPath(paths[id]);
}

/** Orient calibrated wire points so pulses travel from source equipment toward sink. */
export function wirePathForSlot(
  paths: CalibratorPaths,
  anchors: ReturnType<typeof deriveEquipment>,
  slot: WireAnimationSlot,
): string {
  const { pathKey, from, to } = WIRE_SLOT_FLOW[slot];
  return pointsToPath(orientPathBetween(paths[pathKey], anchors[from], anchors[to]));
}

/** @deprecated Use wirePathForSlot — kept for callers that still pass a boolean reverse flag. */
export function wirePathForFlow(
  paths: CalibratorPaths,
  id: SceneWireId,
  againstDefaultDirection: boolean,
): string {
  const points = againstDefaultDirection ? [...paths[id]].reverse() : paths[id];
  return pointsToPath(points);
}

export function sceneEquipmentAnchors(paths: CalibratorPaths) {
  return deriveEquipment(paths);
}

export function mergeSceneConfig(current: SceneConfig, patch: Partial<SceneConfig>): SceneConfig {
  return {
    ...current,
    ...patch,
    equipment: patch.equipment ? { ...current.equipment, ...patch.equipment } : current.equipment,
    paths: patch.paths ? clonePaths(patch.paths) : current.paths,
    updatedAt: new Date().toISOString(),
  };
}
