import { renderHook, act, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { SCENE_CONFIG_STORAGE_KEY } from "./energySceneConfig";
import { loadInitialPaths } from "./energySceneCalibrator";
import {
  hydrateEnergySceneConfig,
  resetEnergySceneConfigStore,
} from "./energySceneConfigStore";
import { useEnergySceneConfig } from "./useEnergySceneConfig";

describe("useEnergySceneConfig", () => {
  beforeEach(async () => {
    resetEnergySceneConfigStore();
    localStorage.clear();
    await hydrateEnergySceneConfig();
  });

  afterEach(() => {
    resetEnergySceneConfigStore();
    localStorage.clear();
  });

  it("loads shared config for every site slug", async () => {
    const paths = loadInitialPaths();
    paths["house-feed"][0] = { x: 42, y: 43 };
    localStorage.setItem(
      SCENE_CONFIG_STORAGE_KEY,
      JSON.stringify({
        photoSource: "default",
        paths,
        equipment: {
          solar: "panel-black",
          inverter: "inverter-standard",
          battery: "battery-tower-white",
        },
        showEquipmentOverlay: true,
        updatedAt: "2026-08-14T12:00:00.000Z",
      }),
    );

    resetEnergySceneConfigStore();
    await hydrateEnergySceneConfig();

    const { result: calibrator } = renderHook(() => useEnergySceneConfig("default"));
    const { result: dashboard } = renderHook(() => useEnergySceneConfig("akarp"));

    expect(calibrator.current.config.paths["house-feed"][0]).toEqual({ x: 42, y: 43 });
    expect(dashboard.current.config.paths["house-feed"][0]).toEqual({ x: 42, y: 43 });
  });

  it("keeps other mounted views in sync after updates", async () => {
    const first = renderHook(() => useEnergySceneConfig("default"));
    const second = renderHook(() => useEnergySceneConfig("summer-house-denmark"));

    act(() => {
      first.result.current.updatePaths((current) => {
        const next = structuredClone(current);
        next["grid-lawn"][0] = { x: 7, y: 8 };
        return next;
      });
    });

    await waitFor(() => {
      expect(second.result.current.config.paths["grid-lawn"][0]).toEqual({ x: 7, y: 8 });
    });

    await waitFor(() => {
      expect(localStorage.getItem(SCENE_CONFIG_STORAGE_KEY)).toContain('"x":7');
    });
  });
});
