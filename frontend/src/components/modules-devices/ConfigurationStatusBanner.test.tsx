import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfigurationStatusBanner } from "@/components/modules-devices/ConfigurationStatusBanner";

describe("ConfigurationStatusBanner", () => {
  it("shows restart required and apply button", async () => {
    const onApply = vi.fn();
    render(
      <ConfigurationStatusBanner
        restartRequired="module"
        configurationStatus="restart_required"
        onApply={onApply}
      />,
    );
    expect(screen.getByText(/Omstart krävs/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Tillämpa ändringar/i }));
    expect(onApply).toHaveBeenCalled();
  });

  it("shows active configuration", () => {
    render(
      <ConfigurationStatusBanner
        restartRequired="none"
        configurationStatus="active"
        effectivelyConfigured
      />,
    );
    expect(screen.getByText(/Konfiguration aktiv/)).toBeInTheDocument();
  });
});
