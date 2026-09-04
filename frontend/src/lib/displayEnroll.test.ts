import { describe, expect, it } from "vitest";

import {
  buildDisplayEnrollUrl,
  displayDeviceTypeLabel,
  displayHomePath,
  isDisplayDevice,
} from "@/lib/displayEnroll";

describe("displayEnroll helpers", () => {
  it("builds enroll url with token and slug", () => {
    expect(buildDisplayEnrollUrl("https://emic.inacloud.se", "emic_dev_token", "akarp")).toBe(
      "https://emic.inacloud.se/api/v1/display/enroll?token=emic_dev_token&slug=akarp",
    );
  });

  it("detects display devices by scope or type", () => {
    expect(isDisplayDevice({ scopes: "display.read", device_type: "tablet" })).toBe(true);
    expect(isDisplayDevice({ scopes: "widget.read", device_type: "phone" })).toBe(true);
    expect(isDisplayDevice({ scopes: "widget.read", device_type: "iphone" })).toBe(false);
  });

  it("labels device types in Swedish", () => {
    expect(displayDeviceTypeLabel("phone")).toBe("Mobil");
    expect(displayDeviceTypeLabel("tablet")).toBe("Surfplatta");
  });

  it("builds display home path", () => {
    expect(displayHomePath("akarp")).toBe("/display/akarp");
  });
});
