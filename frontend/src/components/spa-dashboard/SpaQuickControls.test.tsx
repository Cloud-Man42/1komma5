import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SpaQuickControls } from "./SpaQuickControls";

const mockRunSpaCleaningNow = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    runSpaCleaningNow: (...args: unknown[]) => mockRunSpaCleaningNow(...args),
  };
});

const status = {
  online: true,
  integration_enabled: true,
  data_source: "arctic_spa",
  filter_status: "Idle",
} as const;

describe("SpaQuickControls", () => {
  it("starts cleaning cycle and shows API message", async () => {
    mockRunSpaCleaningNow.mockResolvedValue({
      success: true,
      message: "Filtercykel startad",
      dry_run: false,
    });
    const user = userEvent.setup();

    render(
      <SpaQuickControls
        siteSlug="akarp"
        status={status}
        control={{ smart_control_enabled: true } as never}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Rengöringscykel/i }));

    expect(mockRunSpaCleaningNow).toHaveBeenCalledWith("akarp");
    expect(await screen.findByText("Filtercykel startad")).toBeInTheDocument();
  });

  it("shows API failure message", async () => {
    mockRunSpaCleaningNow.mockResolvedValue({
      success: false,
      message: "Dagens max antal filtercykler är redan nått.",
      dry_run: false,
    });
    const user = userEvent.setup();

    render(
      <SpaQuickControls
        siteSlug="akarp"
        status={status}
        control={{ smart_control_enabled: true } as never}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Rengöringscykel/i }));

    expect(await screen.findByText(/max antal filtercykler/i)).toBeInTheDocument();
  });

  it("disables cleaning when smart control is off", () => {
    render(
      <SpaQuickControls
        siteSlug="akarp"
        status={status}
        control={{ smart_control_enabled: false } as never}
      />,
    );

    expect(screen.getByRole("button", { name: /Rengöringscykel/i })).toBeDisabled();
    expect(screen.getByText(/Aktivera smartstyrning/i)).toBeInTheDocument();
  });
});
