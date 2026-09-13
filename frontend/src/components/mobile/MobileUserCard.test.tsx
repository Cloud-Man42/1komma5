import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MobileUserCard } from "./MobileUserCard";
import type { UserItem } from "@/lib/adminUsersApi";

const user: UserItem = {
  id: 1,
  username: "henrik",
  email: "henrik@example.com",
  firstName: "Henrik",
  lastName: "Melén",
  displayName: "Henrik Melén",
  isActive: true,
  isLocked: false,
  mustChangePassword: false,
  lastLoginAt: "2026-09-12T14:32:00Z",
  roles: [{ id: 1, name: "Admin" }],
  sites: ["akarp", "summer-house-denmark"],
};

describe("MobileUserCard", () => {
  it("renders user summary as card", () => {
    render(<MobileUserCard user={user} />);
    expect(screen.getByText("Henrik Melén")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByText(/akarp/)).toBeInTheDocument();
  });
});
