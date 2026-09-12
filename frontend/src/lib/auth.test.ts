import { describe, expect, it } from "vitest";
import { hasPermission } from "@/lib/auth";

describe("hasPermission", () => {
  it("grants all when wildcard present", () => {
    expect(
      hasPermission(
        {
          id: 1,
          username: "a",
          email: "a@x.com",
          displayName: "A",
          roles: ["SUPER_ADMIN"],
          permissions: ["*"],
          sites: [],
          mustChangePassword: false,
          authMethod: "session",
        },
        "users.read",
      ),
    ).toBe(true);
  });

  it("grants all for SUPER_ADMIN role even without wildcard permission", () => {
    expect(
      hasPermission(
        {
          id: 1,
          username: "admin",
          email: "admin@example.com",
          displayName: "Admin",
          roles: ["SUPER_ADMIN"],
          permissions: [],
          sites: [],
          mustChangePassword: false,
          authMethod: "session",
        },
        "users.read",
      ),
    ).toBe(true);
  });

  it("denies missing permission", () => {
    expect(
      hasPermission(
        {
          id: 1,
          username: "v",
          email: "v@x.com",
          displayName: "V",
          roles: ["VIEWER"],
          permissions: ["dashboard.read"],
          sites: ["akarp"],
          mustChangePassword: false,
          authMethod: "session",
        },
        "users.read",
      ),
    ).toBe(false);
  });
});
