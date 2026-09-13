import { describe, expect, it } from "vitest";
import { clearTenantScopedStorage, tenantStorageKey } from "@/lib/tenantApi";

describe("tenantApi", () => {
  it("builds tenant-scoped storage keys", () => {
    expect(tenantStorageKey(7, "selectedSites")).toBe("tenant:7:selectedSites");
  });

  it("clears tenant-scoped localStorage entries", () => {
    localStorage.setItem("tenant:3:selectedSites", "akarp");
    localStorage.setItem("tenant:3:preferences", "{}");
    localStorage.setItem("tenant:4:selectedSites", "other");
    clearTenantScopedStorage(3);
    expect(localStorage.getItem("tenant:3:selectedSites")).toBeNull();
    expect(localStorage.getItem("tenant:3:preferences")).toBeNull();
    expect(localStorage.getItem("tenant:4:selectedSites")).toBe("other");
  });
});
