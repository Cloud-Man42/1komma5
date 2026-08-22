import { describe, expect, it } from "vitest";
import {
  DEFAULT_EQUIPMENT_VARIANTS,
  equipmentPlacement,
  SOLAR_VARIANTS,
  variantMeta,
} from "./energySceneEquipment";

describe("energySceneEquipment", () => {
  it("exposes three variants per equipment type", () => {
    expect(SOLAR_VARIANTS).toHaveLength(3);
    expect(DEFAULT_EQUIPMENT_VARIANTS.inverter).toBe("inverter-standard");
  });

  it("places equipment relative to anchor point", () => {
    const meta = variantMeta("inverter", "inverter-standard");
    const box = equipmentPlacement({ x: 50, y: 20 }, meta);
    expect(box.x).toBeLessThan(50);
    expect(box.y).toBeLessThan(20);
    expect(box.width).toBe(meta.width);
  });
});
