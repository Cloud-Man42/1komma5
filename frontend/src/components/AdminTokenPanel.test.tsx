import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdminTokenPanel } from "@/components/AdminTokenPanel";
import { getAdminToken } from "@/lib/adminAuth";

describe("AdminTokenPanel", () => {
  it("stores admin token in sessionStorage", () => {
    sessionStorage.clear();
    render(<AdminTokenPanel />);

    fireEvent.change(screen.getByLabelText("Admin-token"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: /Spara admin-token/i }));

    expect(getAdminToken()).toBe("secret");
    expect(screen.getByText(/Admin-token sparat/i)).toBeInTheDocument();
  });
});
