import { describe, expect, it } from "vitest";
import { SPA_HERO_PHOTO, SPA_SIDEBAR_PHOTO, SPA_TUB_TOPDOWN } from "./spaScenePhoto";

describe("spaScenePhoto", () => {
  it("uses the shared spa hero image everywhere", () => {
    expect(SPA_HERO_PHOTO).toBe("/images/spa-hero.png");
    expect(SPA_SIDEBAR_PHOTO).toBe(SPA_HERO_PHOTO);
    expect(SPA_TUB_TOPDOWN).toBe(SPA_HERO_PHOTO);
  });
});
