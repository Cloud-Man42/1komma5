import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import AdminRoleEditPage from "./page";
import { ToastProvider } from "@/components/admin-ui";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "1" }),
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    can: (perm: string) => perm === "roles.read" || perm === "roles.manage",
  }),
}));

vi.mock("@/lib/adminUsersApi", () => ({
  fetchAdminRoles: vi.fn(),
  fetchAdminPermissions: vi.fn(),
}));

import { fetchAdminPermissions, fetchAdminRoles } from "@/lib/adminUsersApi";

describe("AdminRoleEditPage", () => {
  beforeEach(() => {
    vi.mocked(fetchAdminRoles).mockResolvedValue([
      {
        id: 1,
        name: "CUSTOM",
        description: "Custom role",
        isSystemRole: false,
        permissions: [{ id: 10, key: "users.read" }],
      },
    ]);
    vi.mocked(fetchAdminPermissions).mockResolvedValue([
      { id: 10, key: "users.read", name: "Read users", description: "", group: "Users" },
    ]);
  });

  it("renders permission groups for editable role", async () => {
    render(
      <ToastProvider>
        <AdminRoleEditPage />
      </ToastProvider>,
    );
    expect(await screen.findByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Read users")).toBeInTheDocument();
  });
});
