import type { CalibratorPaths } from "./energySceneCalibrator";
import {
  createDefaultSceneConfig,
  cleanupLegacySceneStorage,
  mergeSceneConfig,
  readPersistedSceneConfig,
  writePersistedSceneConfig,
  type SceneConfig,
} from "./energySceneConfig";
import { clearCustomScenePhoto, loadCustomScenePhoto, saveCustomScenePhoto } from "./energyScenePhotoStore";
import { DEFAULT_SCENE_PHOTO, isCustomPhotoUrl } from "./energyScenePhoto";

type Listener = () => void;

let snapshot: SceneConfig = createDefaultSceneConfig();
let hydrated = false;
let hydrating: Promise<void> | null = null;
const listeners = new Set<Listener>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

export function getEnergySceneConfigSnapshot(): SceneConfig {
  return snapshot;
}

export function isEnergySceneConfigHydrated(): boolean {
  return hydrated;
}

export function subscribeEnergySceneConfig(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

async function resolvePhotoUrl(photoSource: "default" | "custom", inlinePhotoUrl?: string): Promise<string> {
  if (photoSource === "custom") {
    if (inlinePhotoUrl && isCustomPhotoUrl(inlinePhotoUrl)) return inlinePhotoUrl;
    const stored = await loadCustomScenePhoto();
    if (stored) return stored;
  }
  return DEFAULT_SCENE_PHOTO;
}

export async function hydrateEnergySceneConfig(): Promise<SceneConfig> {
  if (typeof window === "undefined") return snapshot;
  if (hydrated) return snapshot;
  if (hydrating) {
    await hydrating;
    return snapshot;
  }

  hydrating = (async () => {
    const persisted = readPersistedSceneConfig();
    if (persisted.photoSource === "custom" && persisted.photoUrl && isCustomPhotoUrl(persisted.photoUrl)) {
      await saveCustomScenePhoto(persisted.photoUrl);
      writePersistedSceneConfig({ ...persisted, photoUrl: undefined });
    }

    const photoUrl = await resolvePhotoUrl(persisted.photoSource, persisted.photoUrl);
    snapshot = {
      photoUrl,
      paths: persisted.paths,
      equipment: persisted.equipment,
      showEquipmentOverlay: persisted.showEquipmentOverlay,
      updatedAt: persisted.updatedAt,
    };
    hydrated = true;
    cleanupLegacySceneStorage();
    emit();
  })();

  await hydrating;
  hydrating = null;
  return snapshot;
}

export function resetEnergySceneConfigStore(): void {
  snapshot = createDefaultSceneConfig();
  hydrated = false;
  hydrating = null;
}

async function persistSceneConfig(config: SceneConfig): Promise<void> {
  const photoSource: "default" | "custom" = isCustomPhotoUrl(config.photoUrl) ? "custom" : "default";

  if (photoSource === "custom") {
    await saveCustomScenePhoto(config.photoUrl);
  } else {
    await clearCustomScenePhoto();
  }

  writePersistedSceneConfig({
    photoSource,
    paths: config.paths,
    equipment: config.equipment,
    showEquipmentOverlay: config.showEquipmentOverlay,
    updatedAt: config.updatedAt,
  });
}

export async function commitEnergySceneConfig(config: SceneConfig): Promise<SceneConfig> {
  snapshot = config;
  hydrated = true;
  emit();
  await persistSceneConfig(config);
  emit();
  return snapshot;
}

export function patchEnergySceneConfig(patch: Partial<SceneConfig>): Promise<SceneConfig> {
  const next = mergeSceneConfig(snapshot, patch);
  return commitEnergySceneConfig(next);
}

export function updateEnergyScenePaths(
  updater: CalibratorPaths | ((current: CalibratorPaths) => CalibratorPaths),
): Promise<SceneConfig> {
  const paths = typeof updater === "function" ? updater(snapshot.paths) : updater;
  return patchEnergySceneConfig({ paths });
}

export async function resetEnergySceneConfig(): Promise<SceneConfig> {
  await clearCustomScenePhoto();
  return commitEnergySceneConfig(createDefaultSceneConfig());
}
