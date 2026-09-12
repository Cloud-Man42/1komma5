import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminAuthPrompt } from "@/components/AdminAuthPrompt";
import { getAdminToken, setAdminToken } from "@/lib/adminAuth";

describe("AdminAuthPrompt", () => {
  it("shows invalid-token guidance", () => {
    render(<AdminAuthPrompt issue="invalid" />);
    expect(screen.getByText(/Admin-token ogiltig/i)).toBeInTheDocument();
    expect(screen.getByText(/matchar inte serverns/i)).toBeInTheDocument();
  });

  it("reloads after saving token", () => {
    sessionStorage.clear();
    const reload = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, reload },
    });

    render(<AdminAuthPrompt />);
    fireEvent.change(screen.getByLabelText("Admin-token"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: /Spara och ladda om/i }));

    expect(getAdminToken()).toBe("secret");
    expect(reload).toHaveBeenCalled();
  });
});
