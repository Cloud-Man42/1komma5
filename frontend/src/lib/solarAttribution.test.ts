import { describe, expect, it } from "vitest";
import { SMHI_ATTRIBUTION, smhiAttributionLine } from "@/lib/solarAttribution";

describe("solarAttribution", () => {
  it("includes SMHI in attribution line", () => {
    expect(smhiAttributionLine()).toContain("SMHI");
  });

  it("has link to SMHI open data portal", () => {
    expect(SMHI_ATTRIBUTION.linkUrl).toBe("https://opendata.smhi.se/");
    expect(SMHI_ATTRIBUTION.linkUrl).not.toContain("ladda-ner-meteorologiska");
  });
});
