import { describe, expect, it, beforeEach } from "vitest";

import { adminAuthHeaders, getAdminToken, setAdminToken } from "@/lib/adminAuth";

describe("adminAuth", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns empty token by default", () => {
    expect(getAdminToken()).toBe("");
    expect(adminAuthHeaders()).toEqual({});
  });

  it("stores token in sessionStorage", () => {
    setAdminToken("secret-token");
    expect(getAdminToken()).toBe("secret-token");
    expect(adminAuthHeaders()).toEqual({ Authorization: "Bearer secret-token" });
  });

  it("clears token when empty string is saved", () => {
    setAdminToken("secret-token");
    setAdminToken("");
    expect(getAdminToken()).toBe("");
  });
});
