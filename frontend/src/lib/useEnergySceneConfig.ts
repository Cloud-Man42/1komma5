"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";
import type { CalibratorPaths } from "./energySceneCalibrator";
import {
  commitEnergySceneConfig,
  getEnergySceneConfigSnapshot,
  hydrateEnergySceneConfig,
  isEnergySceneConfigHydrated,
  patchEnergySceneConfig,
  resetEnergySceneConfig,
  subscribeEnergySceneConfig,
  updateEnergyScenePaths,
} from "./energySceneConfigStore";
import { createDefaultSceneConfig, type SceneConfig } from "./energySceneConfig";

export function useEnergySceneConfig(_siteSlug = "default") {
  const config = useSyncExternalStore(
    subscribeEnergySceneConfig,
    getEnergySceneConfigSnapshot,
    createDefaultServerSnapshot,
  );
  const ready = useSyncExternalStore(
    subscribeEnergySceneConfig,
    isEnergySceneConfigHydrated,
    () => false,
  );

  useEffect(() => {
    void hydrateEnergySceneConfig();
  }, []);

  const setConfig = useCallback(
    (updater: SceneConfig | ((current: SceneConfig) => SceneConfig)) => {
      const next =
        typeof updater === "function" ? updater(getEnergySceneConfigSnapshot()) : updater;
      void commitEnergySceneConfig(next);
    },
    [],
  );

  const patchConfig = useCallback((patch: Partial<SceneConfig>) => {
    void patchEnergySceneConfig(patch);
  }, []);

  const updatePaths = useCallback(
    (updater: CalibratorPaths | ((current: CalibratorPaths) => CalibratorPaths)) => {
      void updateEnergyScenePaths(updater);
    },
    [],
  );

  const resetConfig = useCallback(() => {
    void resetEnergySceneConfig();
  }, []);

  return { config, setConfig, patchConfig, updatePaths, resetConfig, ready };
}

function createDefaultServerSnapshot(): SceneConfig {
  return SERVER_SCENE_SNAPSHOT;
}

const SERVER_SCENE_SNAPSHOT = createDefaultSceneConfig();
