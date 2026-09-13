import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AccountPage from "./page";
import { ToastProvider } from "@/components/admin-ui";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    loading: false,
    user: {
      id: 1,
      username: "alice",
      email: "alice@example.com",
      displayName: "Alice A",
      roles: ["USER"],
      sites: ["akarp"],
      mustChangePassword: false,
      authMethod: "session",
    },
  }),
}));

function renderPage() {
  return render(
    <ToastProvider>
      <AccountPage />
    </ToastProvider>,
  );
}

describe("AccountPage", () => {
  it("renders profile read-only fields", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Alice A" })).toBeInTheDocument();
    expect(screen.getAllByText("alice@example.com").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Byt lösenord/i })).toBeInTheDocument();
  });

  it("opens change password modal with match validation hint", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /Byt lösenord/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Lösenorden matchar/i)).toBeInTheDocument();
  });

  it("shows password mismatch validation", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /Byt lösenord/i }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(dialog.querySelector('input[type="password"]') as HTMLInputElement, {
      target: { value: "OldPassword123!" },
    });
    const inputs = dialog.querySelectorAll('input[type="password"], input[type="text"]');
    fireEvent.change(inputs[1] as HTMLInputElement, { target: { value: "NewPassword123!" } });
    fireEvent.change(inputs[2] as HTMLInputElement, { target: { value: "Mismatch123!" } });
    expect(screen.getByText(/Lösenorden matchar/i)).toBeInTheDocument();
  });
});
