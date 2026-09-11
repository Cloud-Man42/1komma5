import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PolicyDiagnosticsPanel } from "@/components/modules-devices/governance/PolicyDiagnosticsPanel";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/governance/diagnostics",
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

const evaluateModulePolicy = vi.fn();

vi.mock("@/lib/api", () => ({
  evaluateModulePolicy: (...args: unknown[]) => evaluateModulePolicy(...args),
}));

describe("PolicyDiagnosticsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays evaluation result from API", async () => {
    evaluateModulePolicy.mockResolvedValue({
      decision: "DENY",
      reason_codes: ["COMMUNITY_NOT_ALLOWED"],
      publisher_tier: "COMMUNITY",
      publisher_status: "ACTIVE",
      control_capable: false,
      policy_version: 1,
      explanation: "COMMUNITY tier is not permitted in production.",
    });
    render(<PolicyDiagnosticsPanel />);
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "demo.module" } });
    fireEvent.change(inputs[1], { target: { value: "community-pub" } });
    fireEvent.click(screen.getByRole("button", { name: "Evaluate" }));
    await waitFor(() => {
      expect(screen.getByTestId("policy-evaluation-result")).toBeInTheDocument();
      expect(screen.getByText(/Result: DENY/)).toBeInTheDocument();
      expect(screen.getByText("COMMUNITY_NOT_ALLOWED")).toBeInTheDocument();
    });
  });

  it("shows error when evaluation fails", async () => {
    evaluateModulePolicy.mockRejectedValue(new Error("Evaluation failed"));
    render(<PolicyDiagnosticsPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate" }));
    await waitFor(() => {
      expect(screen.getByText("Evaluation failed")).toBeInTheDocument();
    });
  });
});
