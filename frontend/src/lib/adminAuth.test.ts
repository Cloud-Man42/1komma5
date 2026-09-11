import { describe, expect, it, beforeEach, vi } from "vitest";

import { adminAuthHeaders, adminFetch, getAdminToken, setAdminToken } from "@/lib/adminAuth";

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

  it("adminFetch attaches bearer token to requests", async () => {
    setAdminToken("secret-token");
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await adminFetch("/api/sites");
    expect(fetchMock).toHaveBeenCalledWith("/api/sites", {
      headers: { Authorization: "Bearer secret-token" },
    });

    vi.unstubAllGlobals();
  });

  it("adminFetch dispatches auth-required event on 401", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 401, ok: false });
    vi.stubGlobal("fetch", fetchMock);
    const events: string[] = [];
    window.addEventListener("emic:admin-auth-required", () => events.push("required"));

    await adminFetch("/api/sites");
    expect(events).toEqual(["required"]);

    vi.unstubAllGlobals();
  });
});
