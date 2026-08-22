import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { loadInitialPaths } from "./energySceneCalibrator";
import {
  SCENE_CONFIG_STORAGE_KEY,
  SCENE_CONFIG_STORAGE_PREFIX,
  readPersistedSceneConfig,
  writePersistedSceneConfig,
} from "./energySceneConfig";
import {
  commitEnergySceneConfig,
  getEnergySceneConfigSnapshot,
  hydrateEnergySceneConfig,
  resetEnergySceneConfigStore,
  updateEnergyScenePaths,
} from "./energySceneConfigStore";

describe("energySceneConfigStore", () => {
  beforeEach(() => {
    resetEnergySceneConfigStore();
    localStorage.clear();
  });

  afterEach(() => {
    resetEnergySceneConfigStore();
    localStorage.clear();
  });

  it("hydrates saved paths into a shared in-memory snapshot", async () => {
    const paths = loadInitialPaths();
    paths["house-feed"][0] = { x: 42, y: 43 };

    writePersistedSceneConfig({
      photoSource: "default",
      paths,
      equipment: {
        solar: "panel-black",
        inverter: "inverter-standard",
        battery: "battery-tower-white",
      },
      showEquipmentOverlay: true,
      updatedAt: "2026-08-14T12:00:00.000Z",
    });

    await hydrateEnergySceneConfig();

    expect(getEnergySceneConfigSnapshot().paths["house-feed"][0]).toEqual({ x: 42, y: 43 });
  });

  it("keeps all subscribers on the same snapshot after path updates", async () => {
    await hydrateEnergySceneConfig();

    await updateEnergyScenePaths((current) => {
      const next = structuredClone(current);
      next["grid-lawn"][0] = { x: 7, y: 8 };
      return next;
    });

    expect(getEnergySceneConfigSnapshot().paths["grid-lawn"][0]).toEqual({ x: 7, y: 8 });
    expect(readPersistedSceneConfig().paths["grid-lawn"][0]).toEqual({ x: 7, y: 8 });
  });

  it("migrates the newest legacy localStorage entry into the shared v2 key", async () => {
    const legacy = loadInitialPaths();
    legacy["solar-inverter"][0] = { x: 5, y: 6 };

    localStorage.setItem(
      `${SCENE_CONFIG_STORAGE_PREFIX}akarp`,
      JSON.stringify({
        photoUrl: "/energy-scene-photo.png",
        paths: legacy,
        equipment: {
          solar: "panel-black",
          inverter: "inverter-standard",
          battery: "battery-tower-white",
        },
        showEquipmentOverlay: true,
        updatedAt: "2026-08-14T12:00:00.000Z",
      }),
    );

    await hydrateEnergySceneConfig();

    expect(localStorage.getItem(SCENE_CONFIG_STORAGE_KEY)).toBeTruthy();
    expect(getEnergySceneConfigSnapshot().paths["solar-inverter"][0]).toEqual({ x: 5, y: 6 });
  });

  it("does not store custom photo data URLs in localStorage when IndexedDB is available", async () => {
    if (typeof indexedDB === "undefined") {
      return;
    }

    await hydrateEnergySceneConfig();

    await commitEnergySceneConfig({
      ...getEnergySceneConfigSnapshot(),
      photoUrl: "data:image/jpeg;base64,abc123",
    });

    const raw = localStorage.getItem(SCENE_CONFIG_STORAGE_KEY);
    expect(raw).toBeTruthy();
    expect(raw).not.toContain("data:image/jpeg;base64,abc123");
    expect(readPersistedSceneConfig().photoSource).toBe("custom");
  });
});
