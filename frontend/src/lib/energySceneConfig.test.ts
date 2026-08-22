import { describe, expect, it, beforeEach, afterEach } from "vitest";
import {
  cleanupLegacySceneStorage,
  createDefaultSceneConfig,
  parseSceneConfig,
  readPersistedSceneConfig,
  resolveSceneConfig,
  SCENE_CONFIG_STORAGE_KEY,
  SCENE_CONFIG_STORAGE_PREFIX,
  sceneConfigStorageKey,
  writePersistedSceneConfig,
  wirePathFromConfig,
} from "./energySceneConfig";
import { loadInitialPaths } from "./energySceneCalibrator";
import { resetEnergySceneConfigStore } from "./energySceneConfigStore";

describe("energySceneConfig", () => {
  beforeEach(() => {
    resetEnergySceneConfigStore();
    localStorage.clear();
  });

  afterEach(() => {
    resetEnergySceneConfigStore();
    localStorage.clear();
  });

  it("creates default config with bundled paths and photo", () => {
    const config = createDefaultSceneConfig();
    expect(config.photoUrl).toContain("energy-scene-photo.png");
    expect(config.paths["solar-inverter"].length).toBeGreaterThanOrEqual(2);
    expect(config.equipment.solar).toBe("panel-black");
    expect(config.showEquipmentOverlay).toBe(true);
  });

  it("builds storage key per site slug", () => {
    expect(sceneConfigStorageKey("hemma")).toBe("energy-scene-config:hemma");
  });

  it("round-trips scene config JSON", () => {
    const config = createDefaultSceneConfig();
    const parsed = parseSceneConfig(JSON.stringify(config));
    expect(parsed?.photoUrl).toBe(config.photoUrl);
    expect(parsed?.equipment.inverter).toBe(config.equipment.inverter);
  });

  it("rejects invalid stored config", () => {
    expect(parseSceneConfig("{}")).toBeNull();
    expect(parseSceneConfig(JSON.stringify({ photoUrl: "/x.png" }))).toBeNull();
  });

  it("defaults showEquipmentOverlay when missing in stored JSON", () => {
    const config = createDefaultSceneConfig();
    const { showEquipmentOverlay: _removed, ...legacy } = config;
    const parsed = parseSceneConfig(JSON.stringify(legacy));
    expect(parsed?.showEquipmentOverlay).toBe(true);
  });

  it("derives wire path strings from config paths", () => {
    const paths = loadInitialPaths();
    expect(wirePathFromConfig(paths, "grid-lawn")).toContain("63.5");
  });

  it("reads and writes the shared v2 storage key", () => {
    const config = createDefaultSceneConfig();
    config.paths["grid-lawn"][0] = { x: 99, y: 88 };

    writePersistedSceneConfig({
      photoSource: "default",
      paths: config.paths,
      equipment: config.equipment,
      showEquipmentOverlay: config.showEquipmentOverlay,
      updatedAt: config.updatedAt,
    });

    expect(readPersistedSceneConfig().paths["grid-lawn"][0]).toEqual({ x: 99, y: 88 });
    expect(localStorage.getItem(SCENE_CONFIG_STORAGE_KEY)).toBeTruthy();
  });

  it("cleans up legacy per-site storage keys", () => {
    localStorage.setItem(`${SCENE_CONFIG_STORAGE_PREFIX}akarp`, "{}");
    localStorage.setItem("energy-scene-calibrator-draft", "{}");
    writePersistedSceneConfig({
      photoSource: "default",
      paths: createDefaultSceneConfig().paths,
      equipment: createDefaultSceneConfig().equipment,
      showEquipmentOverlay: true,
      updatedAt: "2026-08-14T12:00:00.000Z",
    });

    cleanupLegacySceneStorage();

    expect(localStorage.getItem(`${SCENE_CONFIG_STORAGE_PREFIX}akarp`)).toBeNull();
    expect(localStorage.getItem("energy-scene-calibrator-draft")).toBeNull();
    expect(localStorage.getItem(SCENE_CONFIG_STORAGE_KEY)).toBeTruthy();
  });

  it("falls back to newest legacy scene config when shared config is missing", () => {
    const shared = createDefaultSceneConfig();
    shared.paths["grid-lawn"][0] = { x: 99, y: 88 };
    shared.updatedAt = "2026-08-14T10:00:00.000Z";

    const legacy = createDefaultSceneConfig();
    legacy.paths["grid-lawn"][0] = { x: 11, y: 22 };
    legacy.updatedAt = "2026-08-14T12:00:00.000Z";

    const resolved = resolveSceneConfig((slug) => {
      if (slug === "default") return null;
      if (slug === "akarp") return JSON.stringify(legacy);
      if (slug === "hemma") return JSON.stringify(shared);
      return null;
    }, ["akarp", "hemma"]);

    expect(resolved.paths["grid-lawn"][0]).toEqual({ x: 11, y: 22 });
  });

  it("prefers shared scene config over legacy per-site drafts", () => {
    const shared = createDefaultSceneConfig();
    shared.paths["grid-lawn"][0] = { x: 99, y: 88 };

    const legacy = createDefaultSceneConfig();
    legacy.paths["grid-lawn"][0] = { x: 11, y: 22 };

    const resolved = resolveSceneConfig((slug) => {
      if (slug === "default") return JSON.stringify(shared);
      if (slug === "akarp") return JSON.stringify(legacy);
      return null;
    }, ["default", "akarp"]);

    expect(resolved.paths["grid-lawn"][0]).toEqual({ x: 99, y: 88 });
  });
});
