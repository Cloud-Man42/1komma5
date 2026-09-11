import { describe, expect, it } from "vitest";
import { packageErrorLabel, packageStateLabel, trustBadgeLabel } from "@/components/modules-devices/packageErrorLabels";

describe("packageErrorLabels", () => {
  it("maps known error codes", () => {
    expect(packageErrorLabel("SIGNATURE_INVALID")).toContain("signatur");
    expect(packageErrorLabel("PUBLISHER_UNKNOWN")).toContain("betrodd");
    expect(packageErrorLabel("PACKAGE_QUARANTINED")).toContain("karantän");
  });

  it("maps package states", () => {
    expect(packageStateLabel("quarantined")).toBe("Karantän");
    expect(packageStateLabel("installed")).toBe("Installerad");
  });

  it("maps trust badges", () => {
    expect(trustBadgeLabel("install_allowed", false)).toBe("Installation blockerad");
    expect(trustBadgeLabel("publisher_trusted", true)).toBe("Publisher betrodd");
  });
});
