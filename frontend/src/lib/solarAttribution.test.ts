import { describe, expect, it } from "vitest";
import { SMHI_ATTRIBUTION, smhiAttributionLine } from "@/lib/solarAttribution";

describe("solarAttribution", () => {
  it("includes SMHI in attribution line", () => {
    expect(smhiAttributionLine()).toContain("SMHI");
  });

  it("has link to SMHI open data", () => {
    expect(SMHI_ATTRIBUTION.linkUrl).toMatch(/^https:\/\/www\.smhi\.se/);
  });
});
