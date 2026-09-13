import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlatformTenantsPage from "./page";

vi.mock("@/lib/tenantApi", () => ({
  fetchPlatformTenants: vi.fn(),
  createPlatformTenant: vi.fn(),
  updatePlatformTenant: vi.fn(),
  deletePlatformTenant: vi.fn(),
  fetchPlatformTenantMembers: vi.fn(),
  addPlatformTenantMember: vi.fn(),
  removePlatformTenantMember: vi.fn(),
}));

import {
  addPlatformTenantMember,
  createPlatformTenant,
  deletePlatformTenant,
  fetchPlatformTenantMembers,
  fetchPlatformTenants,
  removePlatformTenantMember,
  updatePlatformTenant,
} from "@/lib/tenantApi";

const sampleTenants = [
  {
    id: 1,
    slug: "henrik-home",
    name: "Henrik Home",
    displayName: "Henrik Home",
    status: "active",
    isActive: true,
  },
  {
    id: 2,
    slug: "customer-a",
    name: "Customer A",
    displayName: "Customer A",
    status: "disabled",
    isActive: false,
  },
];

describe("PlatformTenantsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchPlatformTenants).mockResolvedValue(sampleTenants);
    vi.mocked(fetchPlatformTenantMembers).mockResolvedValue([
      {
        tenantUserId: 10,
        userId: 5,
        email: "viewer@example.com",
        displayName: "Viewer",
        isActive: true,
        roles: ["VIEWER"],
      },
    ]);
    vi.mocked(createPlatformTenant).mockResolvedValue({
      id: 3,
      slug: "new-co",
      name: "New Co",
      displayName: "New Co",
      status: "active",
      isActive: true,
    });
    vi.mocked(updatePlatformTenant).mockResolvedValue({
      ...sampleTenants[0],
      isActive: false,
      status: "disabled",
    });
    vi.mocked(addPlatformTenantMember).mockResolvedValue({
      tenantUserId: 11,
      userId: 6,
      email: "alice@example.com",
      displayName: "Alice",
      isActive: true,
      roles: [],
    });
    vi.mocked(removePlatformTenantMember).mockResolvedValue(undefined);
    vi.mocked(deletePlatformTenant).mockResolvedValue(undefined);
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("lists platform tenants", async () => {
    render(<PlatformTenantsPage />);
    await waitFor(() => {
      expect(screen.getByText("Henrik Home")).toBeInTheDocument();
      expect(screen.getByText("Customer A")).toBeInTheDocument();
    });
  });

  it("creates a tenant", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantsPage />);
    await waitFor(() => expect(screen.getByText("Henrik Home")).toBeInTheDocument());

    await user.type(screen.getByLabelText("Name"), "New Co");
    await user.type(screen.getByLabelText("Slug"), "new-co");
    await user.click(screen.getByRole("button", { name: "Create tenant" }));

    await waitFor(() => {
      expect(createPlatformTenant).toHaveBeenCalledWith({
        name: "New Co",
        displayName: "New Co",
        slug: "new-co",
      });
      expect(screen.getByText("(new-co)")).toBeInTheDocument();
    });
  });

  it("manages tenant members", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantsPage />);
    await waitFor(() => expect(screen.getByText("Customer A")).toBeInTheDocument());

    await user.click(screen.getAllByRole("button", { name: "Members" })[1]);
    await waitFor(() => expect(screen.getByText(/viewer@example.com/)).toBeInTheDocument());

    await user.type(screen.getByLabelText("Add user by email"), "alice@example.com");
    await user.click(screen.getByRole("button", { name: "Add member" }));
    await waitFor(() => {
      expect(addPlatformTenantMember).toHaveBeenCalledWith(2, "alice@example.com");
    });

    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    await waitFor(() => {
      expect(removePlatformTenantMember).toHaveBeenCalledWith(2, 5);
    });
  });

  it("deletes a non-default tenant", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantsPage />);
    await waitFor(() => expect(screen.getByText("Customer A")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(deletePlatformTenant).toHaveBeenCalledWith(2);
    });
  });
});
