import { describe, expect, it } from "vitest";
import { isPiSection, piHref, PI_SECTIONS } from "./piSections";

describe("piSections", () => {
  it("builds home and section hrefs", () => {
    expect(piHref("akarp")).toBe("/display/akarp");
    expect(piHref("akarp", "solar")).toBe("/display/akarp/solar");
    expect(piHref("preview", "economy")).toBe("/display/preview/economy");
  });

  it("accepts every registered section key", () => {
    for (const section of PI_SECTIONS) {
      expect(isPiSection(section)).toBe(true);
    }
  });

  it("rejects unknown section keys", () => {
    expect(isPiSection("settings")).toBe(false);
    expect(isPiSection("")).toBe(false);
  });
});
