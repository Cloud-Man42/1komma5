import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ModuleTable } from "./ModuleTable";

vi.mock("@/components/modules-devices/EnableDisableControl", () => ({
  EnableDisableControl: () => <button type="button">Toggle</button>,
}));

describe("ModuleTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders module rows with runtime labels", async () => {
    render(
      <ModuleTable
        siteSlug="akarp"
        onChanged={() => undefined}
        modules={[
          {
            module_id: "integration.chargeamps",
            name: "Charge Amps",
            module_type: "integration",
            enabled: true,
            runtime_status: "unknown",
            health_status: "healthy",
            device_count: 1,
            can_disable: true,
            onboardable: true,
          },
        ]}
      />,
    );
    expect(screen.getByTestId("module-table")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("Runtime status unavailable")).toBeTruthy();
    });
  });
});
