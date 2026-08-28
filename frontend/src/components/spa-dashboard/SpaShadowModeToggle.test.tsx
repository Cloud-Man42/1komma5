import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SpaShadowModeToggle } from "./SpaShadowModeToggle";
import type { SpaControlConfig } from "@/lib/api";

const mockUpdateSpaControlConfig = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    updateSpaControlConfig: (...args: unknown[]) => mockUpdateSpaControlConfig(...args),
  };
});

const control = {
  consumer_id: 1,
  shadow_mode: true,
} as SpaControlConfig;

describe("SpaShadowModeToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateSpaControlConfig.mockResolvedValue({ ...control, shadow_mode: false });
  });

  it("disables shadow mode", async () => {
    const user = userEvent.setup();
    const onChanged = vi.fn();
    render(<SpaShadowModeToggle siteSlug="akarp" control={control} onChanged={onChanged} />);

    await user.click(screen.getByRole("switch", { name: /Shadow mode/i }));

    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith("akarp", { shadow_mode: false });
      expect(onChanged).toHaveBeenCalled();
    });
  });

  it("enables shadow mode", async () => {
    mockUpdateSpaControlConfig.mockResolvedValue({ ...control, shadow_mode: true });
    const user = userEvent.setup();
    render(
      <SpaShadowModeToggle
        siteSlug="akarp"
        control={{ ...control, shadow_mode: false }}
      />,
    );

    await user.click(screen.getByRole("switch", { name: /Shadow mode/i }));

    await waitFor(() => {
      expect(mockUpdateSpaControlConfig).toHaveBeenCalledWith("akarp", { shadow_mode: true });
    });
  });

  it("shows active badge when shadow mode is on", () => {
    render(<SpaShadowModeToggle siteSlug="akarp" control={control} compact />);
    expect(screen.getByText("Aktiv")).toBeInTheDocument();
  });
});
