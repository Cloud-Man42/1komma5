import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RuntimeIsolationPanel } from "@/components/modules-devices/runtime/RuntimeIsolationPanel";

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "token",
}));

vi.mock("@/lib/api", () => ({
  fetchModuleRuntimes: vi.fn().mockResolvedValue({
    runtimes: [],
    runtime_blocked: true,
    active_authorizations: 0,
    message: "Runtime blocked pending isolation verification",
  }),
  fetchRuntimeAuthorizations: vi.fn().mockResolvedValue([]),
  grantRuntimeAuthorization: vi.fn(),
  revokeRuntimeAuthorization: vi.fn(),
}));

describe("RuntimeIsolationPanel", () => {
  it("shows blocked message and authorization table", async () => {
    render(<RuntimeIsolationPanel />);
    expect(await screen.findByTestId("runtime-isolation-panel")).toBeInTheDocument();
    expect(screen.getByText(/Runtime blocked pending isolation verification/i)).toBeInTheDocument();
    expect(screen.getByTestId("runtime-global-blocked")).toHaveTextContent("true");
    expect(screen.getByText(/Pilot Authorizations/i)).toBeInTheDocument();
  });
});
