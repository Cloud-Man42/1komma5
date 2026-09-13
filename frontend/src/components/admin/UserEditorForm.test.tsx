import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UserEditorForm } from "./UserEditorForm";
import { ToastProvider } from "@/components/admin-ui";

vi.mock("@/lib/adminUsersApi", () => ({
  createAdminUser: vi.fn(),
  updateAdminUser: vi.fn(),
  resetAdminUserPassword: vi.fn(),
}));

const roles = [{ id: 1, name: "ADMIN", description: null, isSystemRole: true, permissions: [] }];
const sites = [{ id: 10, slug: "akarp", name: "Åkarp" }];

describe("UserEditorForm", () => {
  it("renders create mode without referencing edit-only reset modal user", () => {
    render(
      <ToastProvider>
        <UserEditorForm
          mode="create"
          roles={roles}
          sites={sites}
          siteSlugToId={new Map([["akarp", 10]])}
          onSaved={vi.fn()}
        />
      </ToastProvider>,
    );
    expect(screen.getByRole("button", { name: "Skapa användare" })).toBeInTheDocument();
    expect(screen.queryByText(/Nytt lösenord för/i)).not.toBeInTheDocument();
  });
});
