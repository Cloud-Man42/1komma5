import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import AdminUsersPage from "./page";
import { ToastProvider } from "@/components/admin-ui";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    can: (perm: string) => perm === "users.read" || perm === "users.update" || perm === "roles.read",
  }),
}));

vi.mock("@/lib/adminUsersApi", () => ({
  fetchAdminUsers: vi.fn(),
  fetchAdminRoles: vi.fn(),
  updateAdminUser: vi.fn(),
}));

import { fetchAdminRoles, fetchAdminUsers } from "@/lib/adminUsersApi";

const sampleUsers = [
  {
    id: 1,
    username: "alice",
    email: "alice@example.com",
    firstName: "Alice",
    lastName: "A",
    displayName: "Alice A",
    isActive: true,
    isLocked: false,
    mustChangePassword: false,
    lastLoginAt: "2026-01-01T10:00:00Z",
    roles: [{ id: 1, name: "ADMIN" }],
    sites: ["akarp"],
  },
  {
    id: 2,
    username: "bob",
    email: "bob@example.com",
    firstName: null,
    lastName: null,
    displayName: "Bob",
    isActive: false,
    isLocked: true,
    mustChangePassword: false,
    lastLoginAt: null,
    roles: [{ id: 2, name: "VIEWER" }],
    sites: [],
  },
];

function renderPage() {
  return render(
    <ToastProvider>
      <AdminUsersPage />
    </ToastProvider>,
  );
}

describe("AdminUsersPage", () => {
  beforeEach(() => {
    vi.mocked(fetchAdminUsers).mockResolvedValue(sampleUsers);
    vi.mocked(fetchAdminRoles).mockResolvedValue([
      { id: 1, name: "ADMIN", description: null, isSystemRole: true, permissions: [] },
      { id: 2, name: "VIEWER", description: null, isSystemRole: true, permissions: [] },
    ]);
  });

  it("renders summary and users", async () => {
    renderPage();
    const table = await screen.findByRole("table");
    expect(table).toHaveTextContent("Alice A");
    expect(screen.getByText("Totalt")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("filters users by search", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("table");
    await user.type(screen.getByLabelText("Sök"), "bob");
    await waitFor(() => {
      expect(screen.getByRole("table")).not.toHaveTextContent("Alice A");
      expect(screen.getByRole("table")).toHaveTextContent("Bob");
    });
  });
});
