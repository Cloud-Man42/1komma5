import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlatformTenantsPage from "./page";

vi.mock("@/lib/tenantApi", () => ({
  fetchPlatformTenants: vi.fn(),
  createPlatformTenant: vi.fn(),
  updatePlatformTenant: vi.fn(),
}));

import {
  createPlatformTenant,
  fetchPlatformTenants,
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
  });

  it("lists platform tenants", async () => {
    render(<PlatformTenantsPage />);
    await waitFor(() => {
      expect(screen.getByText("Henrik Home")).toBeInTheDocument();
      expect(screen.getByText("Customer A")).toBeInTheDocument();
    });
  });

  it("shows platform admin error", async () => {
    vi.mocked(fetchPlatformTenants).mockRejectedValue(new Error("Platform admin required"));
    render(<PlatformTenantsPage />);
    await waitFor(() => {
      expect(screen.getByText("Platform admin required")).toBeInTheDocument();
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

  it("disables an active tenant", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantsPage />);
    await waitFor(() => expect(screen.getByText("Henrik Home")).toBeInTheDocument());

    const disableButtons = screen.getAllByRole("button", { name: "Disable" });
    await user.click(disableButtons[0]);

    await waitFor(() => {
      expect(updatePlatformTenant).toHaveBeenCalledWith(1, { isActive: false });
    });
  });
});
