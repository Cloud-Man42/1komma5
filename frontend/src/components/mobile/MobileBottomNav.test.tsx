import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MobileBottomNav } from "./MobileBottomNav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    can: (p: string) => p === "charging.read" || p === "dashboard.read",
  }),
}));

describe("MobileBottomNav", () => {
  it("renders primary tabs", () => {
    render(<MobileBottomNav />);
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Sites")).toBeInTheDocument();
    expect(screen.getByText("Energy")).toBeInTheDocument();
    expect(screen.getByText("Control")).toBeInTheDocument();
    expect(screen.getByText("More")).toBeInTheDocument();
  });
});
