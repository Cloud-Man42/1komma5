import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MobileControlHubPage from "./page";

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    can: (p: string) => p === "charging.read",
  }),
}));

describe("MobileControlHubPage", () => {
  it("shows charging but hides spa without permission", () => {
    render(<MobileControlHubPage />);
    expect(screen.getByText("Charging")).toBeInTheDocument();
    expect(screen.queryByText("SPA")).not.toBeInTheDocument();
  });
});
