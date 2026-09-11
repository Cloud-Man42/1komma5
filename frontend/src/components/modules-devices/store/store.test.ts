import { describe, expect, it } from "vitest";
import { sanitizeDisplayText } from "@/components/modules-devices/store/SafeMarkdown";
import { isActionable, primaryActionLabel, trustBadgeClass } from "@/components/modules-devices/store/storeLabels";

describe("storeLabels", () => {
  it("maps primary actions", () => {
    expect(primaryActionLabel("INSTALL")).toBe("Install");
    expect(primaryActionLabel("RUNTIME_NOT_PERMITTED")).toBe("Runtime not yet permitted");
  });

  it("detects actionable states", () => {
    expect(isActionable("INSTALL")).toBe(true);
    expect(isActionable("BLOCKED_BY_POLICY")).toBe(false);
  });

  it("assigns trust badge classes", () => {
    expect(trustBadgeClass("OFFICIAL")).toContain("success");
    expect(trustBadgeClass("REVOKED")).toContain("danger");
  });
});

describe("SafeMarkdown sanitizeDisplayText", () => {
  it("strips script tags", () => {
    expect(sanitizeDisplayText("<script>alert(1)</script>Hello")).toBe("Hello");
  });

  it("strips img onerror", () => {
    expect(sanitizeDisplayText('<img src=x onerror=alert(1)>')).not.toContain("onerror");
  });

  it("strips javascript urls", () => {
    expect(sanitizeDisplayText("javascript:alert(1)")).toBe("alert(1)");
  });
});
