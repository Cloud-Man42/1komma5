import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import AdminUserCreatePage from "./page";
import { ToastProvider } from "@/components/admin-ui";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/admin/users/new",
}));

vi.mock("@/lib/useMobileShell", () => ({
  useMobileShell: () => false,
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    can: (perm: string) => perm === "users.create" || perm === "roles.read",
  }),
}));

vi.mock("@/lib/adminUsersApi", () => ({
  fetchAdminRoles: vi.fn(),
  fetchAdminSiteOptions: vi.fn(),
  createAdminUser: vi.fn(),
}));

import { fetchAdminRoles, fetchAdminSiteOptions } from "@/lib/adminUsersApi";

function renderPage() {
  return render(
    <ToastProvider>
      <AdminUserCreatePage />
    </ToastProvider>,
  );
}

describe("AdminUserCreatePage", () => {
  beforeEach(() => {
    vi.mocked(fetchAdminRoles).mockResolvedValue([
      { id: 1, name: "ADMIN", description: null, isSystemRole: true, permissions: [] },
    ]);
    vi.mocked(fetchAdminSiteOptions).mockResolvedValue([
      { id: 10, slug: "akarp", name: "Åkarp" },
    ]);
  });

  it("renders create user form", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Ny användare" })).toBeInTheDocument();
    expect(screen.getByLabelText("E-post")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skapa användare" })).toBeInTheDocument();
  });

  it("does not crash while create form loads roles and sites", async () => {
    renderPage();
    await waitFor(() => {
      expect(fetchAdminRoles).toHaveBeenCalled();
      expect(fetchAdminSiteOptions).toHaveBeenCalled();
    });
    expect(screen.getByText("ADMIN")).toBeInTheDocument();
    expect(screen.getByText("Åkarp")).toBeInTheDocument();
  });
});
